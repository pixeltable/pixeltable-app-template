"""Multimodal RAG -- Unified Knowledge Base.

Upload docs, images, video, and audio. Search across all media types with one query.
"""

import os

import pixeltable as pxt
from pixeltable.functions import openai
from pixeltable.functions import image as pxt_image
from pixeltable.functions.audio import audio_splitter
from pixeltable.functions.document import document_splitter
from pixeltable.functions.huggingface import clip, sentence_transformer
from pixeltable.functions.string import string_splitter
from pixeltable.functions.uuid import uuid7
from pixeltable.functions.video import extract_audio, frame_iterator

import functions

# ---------------------------------------------------------------------------
# Embedding models
# ---------------------------------------------------------------------------
text_embed = sentence_transformer.using(model_id='all-MiniLM-L6-v2')
clip_embed = clip.using(model_id='openai/clip-vit-base-patch32')

HAS_OPENAI = bool(os.environ.get('OPENAI_API_KEY'))

# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------
pxt.create_dir('kb', if_exists='ignore')

# ============================= DOCUMENTS ====================================

documents = pxt.create_table(
    'kb.documents',
    {'id': pxt.String, 'doc': pxt.Document},
    if_exists='ignore',
)
documents.add_computed_column(id=uuid7(), if_exists='ignore')

doc_chunks = pxt.create_view(
    'kb.doc_chunks',
    documents,
    iterator=document_splitter(documents.doc, separators='token_limit', limit=300),
    if_exists='ignore',
)
doc_chunks.add_embedding_index('text', string_embed=text_embed, metric='cosine', if_exists='ignore')


@pxt.query
def search_documents(query_text: str, n: int = 10) -> pxt.Query:
    sim = doc_chunks.text.similarity(string=query_text)
    return (
        doc_chunks
        .select(doc_chunks.text, source=doc_chunks.doc, sim=sim)
        .order_by(sim, asc=False)
        .limit(n)
    )


# ============================= IMAGES =======================================

images = pxt.create_table(
    'kb.images',
    {'id': pxt.String, 'image': pxt.Image, 'caption': pxt.String},
    if_exists='ignore',
)
images.add_computed_column(id=uuid7(), if_exists='ignore')
images.add_computed_column(
    thumbnail=pxt_image.thumbnail(images.image, size=(320, 320)),
    if_exists='ignore',
)
images.add_embedding_index('image', embedding=clip_embed, metric='cosine', if_exists='ignore')


@pxt.query
def search_images(query_text: str, n: int = 10) -> pxt.Query:
    sim = images.image.similarity(string=query_text)
    return (
        images
        .select(images.image, images.caption, sim=sim)
        .order_by(sim, asc=False)
        .limit(n)
    )


# ============================= VIDEO ========================================

videos = pxt.create_table(
    'kb.videos',
    {'id': pxt.String, 'video': pxt.Video},
    if_exists='ignore',
)
videos.add_computed_column(id=uuid7(), if_exists='ignore')

# Frame extraction -> CLIP visual search
video_frames = pxt.create_view(
    'kb.video_frames',
    videos,
    iterator=frame_iterator(videos.video, fps=1.0),
    if_exists='ignore',
)
video_frames.add_embedding_index('frame', embedding=clip_embed, metric='cosine', if_exists='ignore')


@pxt.query
def search_video_frames(query_text: str, n: int = 10) -> pxt.Query:
    sim = video_frames.frame.similarity(string=query_text)
    return (
        video_frames
        .select(video_frames.frame, sim=sim)
        .order_by(sim, asc=False)
        .limit(n)
    )


# Audio track extraction -> Whisper transcription -> text search
videos.add_computed_column(audio_track=extract_audio(videos.video, format='wav'), if_exists='ignore')

video_audio_segments = pxt.create_view(
    'kb.video_audio_segments',
    videos,
    iterator=audio_splitter(videos.audio_track, duration=30.0, overlap=2.0),
    if_exists='ignore',
)

if HAS_OPENAI:
    video_audio_segments.add_computed_column(
        transcription=openai.transcriptions(video_audio_segments.audio_segment, model='whisper-1'),
        if_exists='ignore',
    )
    video_audio_segments.add_computed_column(
        transcript_text=video_audio_segments.transcription.text.astype(pxt.String),
        if_exists='ignore',
    )

    transcript_sentences = pxt.create_view(
        'kb.video_transcript_sentences',
        video_audio_segments,
        iterator=string_splitter(video_audio_segments.transcript_text, separators='sentence'),
        if_exists='ignore',
    )
    transcript_sentences.add_embedding_index('text', string_embed=text_embed, metric='cosine', if_exists='ignore')

    @pxt.query
    def search_video_transcripts(query_text: str, n: int = 10) -> pxt.Query:
        sim = transcript_sentences.text.similarity(string=query_text)
        return (
            transcript_sentences
            .select(transcript_sentences.text, sim=sim)
            .order_by(sim, asc=False)
            .limit(n)
        )


# ============================= AUDIO ========================================

audio_files = pxt.create_table(
    'kb.audio_files',
    {'id': pxt.String, 'audio': pxt.Audio},
    if_exists='ignore',
)
audio_files.add_computed_column(id=uuid7(), if_exists='ignore')

audio_segments = pxt.create_view(
    'kb.audio_segments',
    audio_files,
    iterator=audio_splitter(audio_files.audio, duration=30.0, overlap=2.0),
    if_exists='ignore',
)

if HAS_OPENAI:
    audio_segments.add_computed_column(
        transcription=openai.transcriptions(audio_segments.audio_segment, model='whisper-1'),
        if_exists='ignore',
    )
    audio_segments.add_computed_column(
        transcript_text=audio_segments.transcription.text.astype(pxt.String),
        if_exists='ignore',
    )

    audio_transcript_sentences = pxt.create_view(
        'kb.audio_transcript_sentences',
        audio_segments,
        iterator=string_splitter(audio_segments.transcript_text, separators='sentence'),
        if_exists='ignore',
    )
    audio_transcript_sentences.add_embedding_index(
        'text', string_embed=text_embed, metric='cosine', if_exists='ignore'
    )

    @pxt.query
    def search_audio_transcripts(query_text: str, n: int = 10) -> pxt.Query:
        sim = audio_transcript_sentences.text.similarity(string=query_text)
        return (
            audio_transcript_sentences
            .select(audio_transcript_sentences.text, sim=sim)
            .order_by(sim, asc=False)
            .limit(n)
        )


# ============================= CROSS-MODAL SEARCH ===========================


def search_knowledge(query_text: str, n: int = 20) -> list[dict]:
    """Search ALL modalities and return merged, ranked results."""
    results: list[dict] = []

    results.extend(search_documents(query_text, n=n).collect().to_pandas().to_dict('records'))
    results.extend(search_images(query_text, n=n).collect().to_pandas().to_dict('records'))
    results.extend(search_video_frames(query_text, n=n).collect().to_pandas().to_dict('records'))

    if HAS_OPENAI:
        results.extend(search_video_transcripts(query_text, n=n).collect().to_pandas().to_dict('records'))
        results.extend(search_audio_transcripts(query_text, n=n).collect().to_pandas().to_dict('records'))

    results.sort(key=lambda r: r.get('sim', 0), reverse=True)
    return results[:n]


def ask_question(question: str, n_context: int = 10) -> dict:
    """Retrieve cross-modal context and generate an LLM answer.

    Returns {'answer': str, 'context': list[dict]}.
    Requires OPENAI_API_KEY.
    """
    if not HAS_OPENAI:
        return {'answer': 'OPENAI_API_KEY not set -- cannot generate answer.', 'context': []}

    context = search_knowledge(question, n=n_context)
    context_block = '\n\n---\n\n'.join(
        str(r.get('text', r.get('caption', '[media result]'))) for r in context
    )

    messages = [
        {
            'role': 'system',
            'content': (
                'You are a helpful knowledge-base assistant. Answer the user question using ONLY the '
                'provided context. If the context is insufficient, say so. Cite the source modality '
                '(document, image, video, audio) when relevant.'
            ),
        },
        {
            'role': 'user',
            'content': f'Context:\n{context_block}\n\nQuestion:\n{question}',
        },
    ]

    # Direct SDK call for the chat endpoint (not a computed column)
    import openai as openai_sdk

    client = openai_sdk.OpenAI()
    response = client.chat.completions.create(model='gpt-4o-mini', messages=messages)
    answer = response.choices[0].message.content

    return {'answer': answer, 'context': context}


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print('Schema initialized.')
