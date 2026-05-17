"""Audio & Podcast Intelligence -- self-hosted transcription, summarization, and semantic search."""

import os

import pixeltable as pxt
from pixeltable.functions.audio import audio_splitter
from pixeltable.functions.huggingface import sentence_transformer
from pixeltable.functions.string import string_splitter
from pixeltable.functions.uuid import uuid7

import functions

HAVE_OPENAI = bool(os.environ.get('OPENAI_API_KEY'))

if HAVE_OPENAI:
    from pixeltable.functions import openai

EMBED_FN = sentence_transformer.using(model_id='all-MiniLM-L6-v2')

# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------
pxt.create_dir('audiointel', if_exists='ignore')

# ---------------------------------------------------------------------------
# Base table -- one row per audio file
# ---------------------------------------------------------------------------
audio_files = pxt.create_table(
    'audiointel.audio_files',
    {
        'audio': pxt.Audio,
        'title': pxt.String,
        'source': pxt.String,
        'uuid': pxt.String,
        'timestamp': pxt.Timestamp,
    },
    primary_key='uuid',
    if_exists='ignore',
)
audio_files.add_computed_column(uuid=uuid7(), if_exists='ignore')

# ---------------------------------------------------------------------------
# Audio chunking -- 30-second segments with 5s overlap
# ---------------------------------------------------------------------------
chunks = pxt.create_view(
    'audiointel.chunks',
    audio_files,
    iterator=audio_splitter(audio_files.audio, duration=30.0, overlap=5.0),
    if_exists='ignore',
)

# ---------------------------------------------------------------------------
# Transcription (OpenAI Whisper API or local whisper)
# ---------------------------------------------------------------------------
if HAVE_OPENAI:
    chunks.add_computed_column(
        transcription=openai.transcriptions(chunks.audio_segment, model='whisper-1'),
        if_exists='ignore',
    )
    chunks.add_computed_column(
        transcript_text=chunks.transcription.text.astype(pxt.String),
        if_exists='ignore',
    )
# Local alternative:
# from pixeltable.functions.whisper import transcribe as whisper_transcribe
# chunks.add_computed_column(
#     transcription=whisper_transcribe(chunks.audio_segment, model='base.en'),
#     if_exists='ignore',
# )
# chunks.add_computed_column(transcript_text=chunks.transcription['text'].astype(pxt.String), if_exists='ignore')

# ---------------------------------------------------------------------------
# Sentence splitting on transcript text
# ---------------------------------------------------------------------------
if HAVE_OPENAI:
    sentences = pxt.create_view(
        'audiointel.sentences',
        chunks,
        iterator=string_splitter(chunks.transcript_text, separators='sentence'),
        if_exists='ignore',
    )

    sentences.add_embedding_index(
        'text',
        string_embed=EMBED_FN,
        if_exists='ignore',
    )

# ---------------------------------------------------------------------------
# Per-chunk summary (LLM)
# ---------------------------------------------------------------------------
if HAVE_OPENAI:
    chunks.add_computed_column(
        summary=openai.chat_completions(
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a concise summarizer. Summarize the following audio transcript chunk '
                        'in 2-3 sentences. Focus on key points, decisions, and action items.'
                    ),
                },
                {'role': 'user', 'content': chunks.transcript_text},
            ],
            model='gpt-4.1-mini',
        ),
        if_exists='ignore',
    )
    chunks.add_computed_column(
        summary_text=chunks.summary.choices[0].message.content.astype(pxt.String),
        if_exists='ignore',
    )


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------
@pxt.query
def search_transcripts(query_text: str, limit: int = 10):
    """Semantic search across all transcripts."""
    sents = pxt.get_table('audiointel.sentences')
    sim = sents.text.similarity(string=query_text)
    return sents.order_by(sim, asc=False).limit(limit).select(sents.text, sim=sim)


@pxt.query
def search_in_recording(recording_title: str, query_text: str, limit: int = 10):
    """Semantic search within a specific recording."""
    sents = pxt.get_table('audiointel.sentences')
    files = pxt.get_table('audiointel.audio_files')
    sim = sents.text.similarity(string=query_text)
    return (
        sents.where(files.title == recording_title)
        .order_by(sim, asc=False)
        .limit(limit)
        .select(sents.text, sim=sim)
    )


@pxt.query
def list_recordings():
    """List all audio files with metadata."""
    files = pxt.get_table('audiointel.audio_files')
    return files.select(files.title, files.source, files.timestamp, files.uuid)


@pxt.query
def get_transcript(recording_title: str):
    """Full transcript of a recording, ordered by segment start time."""
    chnks = pxt.get_table('audiointel.chunks')
    files = pxt.get_table('audiointel.audio_files')
    return (
        chnks.where(files.title == recording_title)
        .order_by(chnks.segment_start)
        .select(chnks.transcript_text, chnks.segment_start, chnks.segment_end)
    )


@pxt.query
def get_summary(recording_title: str):
    """Per-chunk summaries for a recording, ordered by segment start time."""
    chnks = pxt.get_table('audiointel.chunks')
    files = pxt.get_table('audiointel.audio_files')
    return (
        chnks.where(files.title == recording_title)
        .order_by(chnks.segment_start)
        .select(chnks.summary_text, chnks.segment_start, chnks.segment_end)
    )



# functions.generate_full_summary is available as a UDF for the API layer
