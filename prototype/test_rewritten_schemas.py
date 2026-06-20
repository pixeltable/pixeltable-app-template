"""Tests that validate the three rewritten schemas structurally.

Uses dry_run mode (no Pixeltable import needed) to verify:
- All expected models are registered
- Dependency ordering is correct
- Stored/computed columns are captured
- Indexes are declared
- Conditional features work

Also produces the line-count comparison table.
"""

import os
import pytest

from pxt_declarative import (
    Column,
    EmbeddingIndex,
    Model,
    ViewModel,
    clear_registry,
    create_all,
    list_models,
)


@pytest.fixture(autouse=True)
def clean_registry():
    clear_registry()
    yield
    clear_registry()


# ---------------------------------------------------------------------------
# Helpers: placeholder Pixeltable types + functions for schema definitions
# ---------------------------------------------------------------------------

class _PxtTypes:
    Video = "pxt.Video"
    String = "pxt.String"
    Timestamp = "pxt.Timestamp"
    Image = "pxt.Image"
    Document = "pxt.Document"
    Audio = "pxt.Audio"
    Int = "pxt.Int"
    Float = "pxt.Float"

pxt = _PxtTypes


def uuid7():
    return "uuid7()"


def extract_audio(col, format="mp3"):
    return ("extract_audio", col, format)


def frame_iterator(video=None, fps=1.0, keyframes_only=False):
    return ("frame_iterator", video, fps, keyframes_only)


def audio_splitter(audio=None, duration=30.0, overlap=0.0):
    return ("audio_splitter", audio, duration, overlap)


def document_splitter(document=None, separators="sentence", metadata=None, limit=None):
    return ("document_splitter", document, separators, metadata, limit)


def string_splitter(text=None, separators="sentence"):
    return ("string_splitter", text, separators)


def whisper_transcribe(audio, model="base.en"):
    return ("whisper_transcribe", audio, model)


def pxt_image_thumbnail(img, size=(320, 320)):
    return ("thumbnail", img, size)


def pxt_image_b64_encode(img, fmt=None):
    return ("b64_encode", img, fmt)


def messages(**kwargs):
    return ("messages", kwargs)


def invoke_tools(tools, response):
    return ("invoke_tools", tools, response)


def transcriptions(audio, model="whisper-1"):
    return ("transcriptions", audio, model)


text_embed = "sentence_transformer.using(all-MiniLM-L6-v2)"
clip_embed = "clip.using(openai/clip-vit-base-patch32)"


# ---------------------------------------------------------------------------
# Test: Video Search schema (Medium complexity)
# ---------------------------------------------------------------------------

class TestVideoSearchSchema:
    def _define_schema(self):
        class Videos(Model):
            __tablename__ = "videointel.videos"
            __primary_key__ = ["uuid"]
            video: pxt.Video
            title: pxt.String
            uuid: pxt.String = uuid7()
            timestamp: pxt.Timestamp
            audio = extract_audio(Column.video, format="mp3")

        class Frames(ViewModel):
            __tablename__ = "videointel.frames"
            __base__ = frame_iterator(video=Videos.video, fps=1.0)
            thumbnail = pxt_image_b64_encode(
                pxt_image_thumbnail(Column.frame, size=(320, 320)))
            __indexes__ = [
                EmbeddingIndex(Column.frame, idx_name="frames_clip_idx",
                               embedding=clip_embed)
            ]

        class AudioChunks(ViewModel):
            __tablename__ = "videointel.audio_chunks"
            __base__ = audio_splitter(audio=Videos.audio, duration=30.0)
            transcription = whisper_transcribe(Column.audio_segment, model="base.en")

        class TranscriptSentences(ViewModel):
            __tablename__ = "videointel.transcript_sentences"
            __parent__ = AudioChunks
            __filter__ = Column.transcription != None
            __iterator__ = string_splitter(
                text=AudioChunks.transcription.text, separators="sentence")
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="transcript_text_idx",
                               string_embed=text_embed)
            ]

        return Videos, Frames, AudioChunks, TranscriptSentences

    def test_all_models_registered(self):
        self._define_schema()
        models = list_models("videointel")
        assert len(models) == 4
        assert set(models.keys()) == {
            "videointel.videos", "videointel.frames",
            "videointel.audio_chunks", "videointel.transcript_sentences",
        }

    def test_topological_order(self):
        self._define_schema()
        plan = create_all("videointel", dry_run=True)
        order = plan["order"]
        assert order[0] == "videointel.videos"
        assert order.index("videointel.audio_chunks") < order.index("videointel.transcript_sentences")

    def test_videos_stored_columns(self):
        Videos, *_ = self._define_schema()
        assert set(Videos._pxt_stored_columns.keys()) == {"video", "title", "uuid", "timestamp"}

    def test_videos_computed_columns(self):
        Videos, *_ = self._define_schema()
        assert "audio" in Videos._pxt_computed_columns

    def test_frames_indexes(self):
        _, Frames, *_ = self._define_schema()
        assert len(Frames._pxt_indexes) == 1
        assert Frames._pxt_indexes[0].idx_name == "frames_clip_idx"

    def test_frames_computed_columns(self):
        _, Frames, *_ = self._define_schema()
        assert "thumbnail" in Frames._pxt_computed_columns

    def test_audio_chunks_computed(self):
        _, _, AudioChunks, _ = self._define_schema()
        assert "transcription" in AudioChunks._pxt_computed_columns

    def test_transcript_sentences_filter(self):
        _, _, _, TranscriptSentences = self._define_schema()
        assert TranscriptSentences._pxt_view_filter is not None
        assert TranscriptSentences._pxt_view_iterator is not None


# ---------------------------------------------------------------------------
# Test: Knowledge Base schema (Simple, conditional OpenAI)
# ---------------------------------------------------------------------------

class TestKnowledgeBaseSchema:
    def _define_schema(self, has_openai=False):
        class Documents(Model):
            __tablename__ = "kb.documents"
            __primary_key__ = ["id"]
            id: pxt.String = uuid7()
            doc: pxt.Document

        class DocChunks(ViewModel):
            __tablename__ = "kb.doc_chunks"
            __base__ = document_splitter(Documents.doc, separators="token_limit", limit=300)
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="doc_text_idx",
                               string_embed=text_embed, metric="cosine")
            ]

        class Images(Model):
            __tablename__ = "kb.images"
            __primary_key__ = ["id"]
            id: pxt.String = uuid7()
            image: pxt.Image
            caption: pxt.String
            thumbnail = pxt_image_thumbnail(Column.image, size=(320, 320))
            __indexes__ = [
                EmbeddingIndex(Column.image, idx_name="image_clip_idx",
                               embedding=clip_embed, metric="cosine")
            ]

        class Videos(Model):
            __tablename__ = "kb.videos"
            __primary_key__ = ["id"]
            id: pxt.String = uuid7()
            video: pxt.Video
            audio_track = extract_audio(Column.video, format="wav")

        class VideoFrames(ViewModel):
            __tablename__ = "kb.video_frames"
            __base__ = frame_iterator(Videos.video, fps=1.0)
            __indexes__ = [
                EmbeddingIndex(Column.frame, idx_name="frame_clip_idx",
                               embedding=clip_embed, metric="cosine")
            ]

        class VideoAudioSegments(ViewModel):
            __tablename__ = "kb.video_audio_segments"
            __base__ = audio_splitter(Videos.audio_track, duration=30.0, overlap=2.0)

        class AudioFiles(Model):
            __tablename__ = "kb.audio_files"
            __primary_key__ = ["id"]
            id: pxt.String = uuid7()
            audio: pxt.Audio

        class AudioSegments(ViewModel):
            __tablename__ = "kb.audio_segments"
            __base__ = audio_splitter(AudioFiles.audio, duration=30.0, overlap=2.0)

        if has_openai:
            VideoAudioSegments.register_column(
                "transcription", transcriptions(Column.audio_segment))
            VideoAudioSegments.register_column(
                "transcript_text", Column.transcription.text)

            class VideoTranscriptSentences(ViewModel):
                __tablename__ = "kb.video_transcript_sentences"
                __parent__ = VideoAudioSegments
                __filter__ = Column.transcript_text != None
                __iterator__ = string_splitter(
                    VideoAudioSegments.transcript_text, separators="sentence")
                __indexes__ = [
                    EmbeddingIndex(Column.text, idx_name="video_transcript_idx",
                                   string_embed=text_embed, metric="cosine")
                ]

            AudioSegments.register_column(
                "transcription", transcriptions(Column.audio_segment))
            AudioSegments.register_column(
                "transcript_text", Column.transcription.text)

            class AudioTranscriptSentences(ViewModel):
                __tablename__ = "kb.audio_transcript_sentences"
                __parent__ = AudioSegments
                __filter__ = Column.transcript_text != None
                __iterator__ = string_splitter(
                    AudioSegments.transcript_text, separators="sentence")
                __indexes__ = [
                    EmbeddingIndex(Column.text, idx_name="audio_transcript_idx",
                                   string_embed=text_embed, metric="cosine")
                ]

        return locals()

    def test_base_models_without_openai(self):
        self._define_schema(has_openai=False)
        models = list_models("kb")
        assert len(models) == 8
        assert "kb.video_transcript_sentences" not in models
        assert "kb.audio_transcript_sentences" not in models

    def test_all_models_with_openai(self):
        self._define_schema(has_openai=True)
        models = list_models("kb")
        assert len(models) == 10
        assert "kb.video_transcript_sentences" in models
        assert "kb.audio_transcript_sentences" in models

    def test_ordering_without_openai(self):
        self._define_schema(has_openai=False)
        plan = create_all("kb", dry_run=True)
        order = plan["order"]
        # Tables before their views
        assert order.index("kb.documents") < order.index("kb.doc_chunks")
        assert order.index("kb.videos") < order.index("kb.video_frames")
        assert order.index("kb.videos") < order.index("kb.video_audio_segments")
        assert order.index("kb.audio_files") < order.index("kb.audio_segments")

    def test_ordering_with_openai(self):
        self._define_schema(has_openai=True)
        plan = create_all("kb", dry_run=True)
        order = plan["order"]
        assert order.index("kb.video_audio_segments") < order.index("kb.video_transcript_sentences")
        assert order.index("kb.audio_segments") < order.index("kb.audio_transcript_sentences")

    def test_documents_shape(self):
        schema = self._define_schema(has_openai=False)
        Docs = schema["Documents"]
        assert set(Docs._pxt_stored_columns.keys()) == {"id", "doc"}

    def test_images_co_located_index(self):
        schema = self._define_schema(has_openai=False)
        Images = schema["Images"]
        assert len(Images._pxt_indexes) == 1
        assert Images._pxt_indexes[0].idx_name == "image_clip_idx"
        assert "thumbnail" in Images._pxt_computed_columns


# ---------------------------------------------------------------------------
# Test: Chat Agent schema (Medium, conditional Anthropic)
# ---------------------------------------------------------------------------

class TestChatAgentSchema:
    def _define_schema(self, has_anthropic=False):
        class Knowledge(Model):
            __tablename__ = "agent.knowledge"
            __primary_key__ = ["uuid"]
            text: pxt.String
            title: pxt.String
            source: pxt.String
            uuid: pxt.String = uuid7()
            timestamp: pxt.Timestamp

        class Sentences(ViewModel):
            __tablename__ = "agent.sentences"
            __base__ = string_splitter(text=Knowledge.text, separators="sentence")
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="knowledge_embed",
                               string_embed=text_embed)
            ]

        class Conversations(Model):
            __tablename__ = "agent.conversations"
            __primary_key__ = ["uuid"]
            role: pxt.String
            content: pxt.String
            conversation_id: pxt.String
            user_id: pxt.String
            uuid: pxt.String = uuid7()
            timestamp: pxt.Timestamp
            __indexes__ = [
                EmbeddingIndex(Column.content, idx_name="conversations_embed",
                               string_embed=text_embed)
            ]

        class AgentTable(Model):
            __tablename__ = "agent.agent"
            __primary_key__ = ["uuid"]
            prompt: pxt.String
            conversation_id: pxt.String
            system_prompt: pxt.String
            max_tokens: pxt.Int
            temperature: pxt.Float
            uuid: pxt.String = uuid7()
            timestamp: pxt.Timestamp

        if has_anthropic:
            AgentTable.register_column("memory_context", Column.prompt)
            AgentTable.register_column("knowledge_context", Column.prompt)
            AgentTable.register_column("initial_response", messages(
                model="claude-sonnet-4-20250514",
                messages=[{"role": "user", "content": Column.prompt}],
            ))
            AgentTable.register_column("tool_output", Column.initial_response)
            AgentTable.register_column("context", Column.prompt)
            AgentTable.register_column("final_response", messages(
                model="claude-sonnet-4-20250514",
                messages=[{"role": "user", "content": Column.context}],
            ))
            AgentTable.register_column("answer", Column.final_response.content[0].text)

        return Knowledge, Sentences, Conversations, AgentTable

    def test_base_models(self):
        self._define_schema(has_anthropic=False)
        models = list_models("agent")
        assert set(models.keys()) == {
            "agent.knowledge", "agent.sentences",
            "agent.conversations", "agent.agent",
        }

    def test_agent_pipeline_columns(self):
        _, _, _, AgentTable = self._define_schema(has_anthropic=True)
        all_cols = list(AgentTable._pxt_registered_columns.keys())
        assert all_cols == [
            "memory_context", "knowledge_context", "initial_response",
            "tool_output", "context", "final_response", "answer",
        ]

    def test_agent_pipeline_disabled(self):
        _, _, _, AgentTable = self._define_schema(has_anthropic=False)
        assert len(AgentTable._pxt_registered_columns) == 0

    def test_ordering(self):
        self._define_schema(has_anthropic=False)
        plan = create_all("agent", dry_run=True)
        order = plan["order"]
        assert order.index("agent.knowledge") < order.index("agent.sentences")

    def test_conversations_index_co_located(self):
        _, _, Conversations, _ = self._define_schema(has_anthropic=False)
        assert len(Conversations._pxt_indexes) == 1
        assert Conversations._pxt_indexes[0].idx_name == "conversations_embed"


# ---------------------------------------------------------------------------
# Test: Backend schema (Hard -- full agent pipeline)
# ---------------------------------------------------------------------------

class TestBackendSchema:
    def _define_schema(self):
        ns = "starter"

        class Documents(Model):
            __tablename__ = f"{ns}.documents"
            __primary_key__ = ["uuid"]
            document: pxt.Document
            uuid: pxt.String = uuid7()
            timestamp: pxt.Timestamp

        class Chunks(ViewModel):
            __tablename__ = f"{ns}.chunks"
            __base__ = document_splitter(
                document=Documents.document,
                separators="page, sentence",
                metadata="title, heading, page",
            )
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="chunks_text_embed",
                               string_embed=text_embed)
            ]

        class Images(Model):
            __tablename__ = f"{ns}.images"
            __primary_key__ = ["uuid"]
            image: pxt.Image
            uuid: pxt.String = uuid7()
            timestamp: pxt.Timestamp
            thumbnail = pxt_image_b64_encode(
                pxt_image_thumbnail(Column.image, size=(320, 320)))
            __indexes__ = [
                EmbeddingIndex(Column.image, idx_name="images_clip_embed",
                               embedding=clip_embed)
            ]

        class Videos(Model):
            __tablename__ = f"{ns}.videos"
            __primary_key__ = ["uuid"]
            video: pxt.Video
            uuid: pxt.String = uuid7()
            timestamp: pxt.Timestamp
            audio = extract_audio(Column.video, format="mp3")

        class VideoFrames(ViewModel):
            __tablename__ = f"{ns}.video_frames"
            __base__ = frame_iterator(video=Videos.video, keyframes_only=True)
            frame_thumbnail = pxt_image_b64_encode(
                pxt_image_thumbnail(Column.frame, size=(320, 320)))
            __indexes__ = [
                EmbeddingIndex(Column.frame, idx_name="frames_clip_embed",
                               embedding=clip_embed)
            ]

        class VideoAudioChunks(ViewModel):
            __tablename__ = f"{ns}.video_audio_chunks"
            __base__ = audio_splitter(audio=Videos.audio, duration=30.0)
            transcription = transcriptions(audio=Column.audio_segment)

        class VideoSentences(ViewModel):
            __tablename__ = f"{ns}.video_sentences"
            __parent__ = VideoAudioChunks
            __filter__ = Column.transcription != None
            __iterator__ = string_splitter(
                text=VideoAudioChunks.transcription.text, separators="sentence")
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="sentences_text_embed",
                               string_embed=text_embed)
            ]

        class ChatHistory(Model):
            __tablename__ = f"{ns}.chat_history"
            role: pxt.String
            content: pxt.String
            conversation_id: pxt.String
            timestamp: pxt.Timestamp
            __indexes__ = [
                EmbeddingIndex(Column.content, idx_name="chat_content_embed",
                               string_embed=text_embed)
            ]

        class AgentPipeline(Model):
            __tablename__ = f"{ns}.agent"
            prompt: pxt.String
            conversation_id: pxt.String
            timestamp: pxt.Timestamp
            initial_system_prompt: pxt.String
            final_system_prompt: pxt.String
            max_tokens: pxt.Int
            temperature: pxt.Float

            initial_response = messages(
                model="claude-3.5-sonnet",
                messages=[{"role": "user", "content": Column.prompt}],
            )
            tool_output = Column.initial_response
            doc_context = Column.prompt
            image_context = Column.prompt
            video_frame_context = Column.prompt
            chat_memory_context = Column.prompt
            history_context = Column.conversation_id
            multimodal_context = Column.prompt
            final_messages = Column.history_context
            final_response = messages(
                model="claude-3.5-sonnet",
                messages=Column.final_messages,
            )
            answer = Column.final_response.content[0].text

        return ns, locals()

    def test_all_9_entities(self):
        ns, _ = self._define_schema()
        models = list_models(ns)
        assert len(models) == 9

    def test_ordering(self):
        ns, _ = self._define_schema()
        plan = create_all(ns, dry_run=True)
        order = plan["order"]

        assert order.index(f"{ns}.documents") < order.index(f"{ns}.chunks")
        assert order.index(f"{ns}.videos") < order.index(f"{ns}.video_frames")
        assert order.index(f"{ns}.videos") < order.index(f"{ns}.video_audio_chunks")
        assert order.index(f"{ns}.video_audio_chunks") < order.index(f"{ns}.video_sentences")

    def test_agent_pipeline_11_computed_columns(self):
        _, schema = self._define_schema()
        Agent = schema["AgentPipeline"]
        computed = list(Agent._pxt_computed_columns.keys())
        assert len(computed) == 11
        assert computed[0] == "initial_response"
        assert computed[-1] == "answer"

    def test_agent_pipeline_column_order(self):
        _, schema = self._define_schema()
        Agent = schema["AgentPipeline"]
        computed = list(Agent._pxt_computed_columns.keys())
        expected_order = [
            "initial_response", "tool_output",
            "doc_context", "image_context", "video_frame_context",
            "chat_memory_context", "history_context",
            "multimodal_context", "final_messages",
            "final_response", "answer",
        ]
        assert computed == expected_order

    def test_stored_columns_count(self):
        _, schema = self._define_schema()
        Agent = schema["AgentPipeline"]
        stored = list(Agent._pxt_stored_columns.keys())
        assert len(stored) == 7
        assert "prompt" in stored
        assert "temperature" in stored


# ---------------------------------------------------------------------------
# Line count comparison
# ---------------------------------------------------------------------------

class TestLineCountComparison:
    """Count lines in original vs declarative schemas."""

    def _count_lines(self, filepath):
        if not os.path.exists(filepath):
            return 0
        with open(filepath) as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))

    def test_print_comparison(self, capsys):
        base = os.path.dirname(__file__)
        repo_root = os.path.dirname(base)

        originals = {
            "video-search": os.path.join(repo_root, "templates/video-search/schema.py"),
            "knowledge-base": os.path.join(repo_root, "templates/knowledge-base/schema.py"),
            "chat-agent": os.path.join(repo_root, "templates/chat-agent/schema.py"),
            "backend": os.path.join(repo_root, "backend/setup_pixeltable.py"),
        }

        declaratives = {
            "video-search": os.path.join(base, "video_search_declarative.py"),
            "knowledge-base": os.path.join(base, "knowledge_base_declarative.py"),
            "chat-agent": os.path.join(base, "chat_agent_declarative.py"),
            "backend": os.path.join(base, "backend_declarative.py"),
        }

        print("\n")
        print("=" * 72)
        print("LINE COUNT COMPARISON: Original (imperative) vs Declarative")
        print("=" * 72)
        print(f"{'Template':<20} {'Original':>10} {'Declarative':>12} {'Reduction':>10}")
        print("-" * 72)

        for name in originals:
            orig_lines = self._count_lines(originals[name])
            decl_lines = self._count_lines(declaratives[name])
            if orig_lines > 0:
                reduction = f"{(1 - decl_lines / orig_lines) * 100:.0f}%"
            else:
                reduction = "N/A"
            print(f"{name:<20} {orig_lines:>10} {decl_lines:>12} {reduction:>10}")

        print("=" * 72)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
