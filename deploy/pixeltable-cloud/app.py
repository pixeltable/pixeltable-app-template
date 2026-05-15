"""Pixeltable schema for Pixeltable Cloud deployment.

Imported by pxt serve / pxt deploy via the `modules` field in pixeltable.toml.

Requires:
    OPENAI_API_KEY    Used for image descriptions (gpt-4o-mini vision) and
                      document summarization + sentiment (gpt-4o-mini).
"""

import pixeltable as pxt
from pixeltable.functions.openai import chat_completions

pxt.create_dir('pipeline', if_exists='ignore')


# ── Images ────────────────────────────────────────────────────────────────────
# Upload an image → one-sentence description via gpt-4o-mini vision.

images = pxt.create_table('pipeline.images', {'image': pxt.Image}, if_exists='ignore')
images.add_computed_column(
    img_response=chat_completions(
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': 'Describe this image in one sentence.',
                },
                {'type': 'image_url', 'image_url': images.image},
            ],
        }],
        model='gpt-4o-mini',
    ),
    if_exists='ignore',
)
images.add_computed_column(
    description=images.img_response['choices'][0]['message']['content'],
    if_exists='ignore',
)


# ── Documents ─────────────────────────────────────────────────────────────────
# Submit text → one-sentence summary via gpt-4o-mini.

documents = pxt.create_table('pipeline.documents', {'body': pxt.String}, if_exists='ignore')
documents.add_computed_column(
    doc_response=chat_completions(
        messages=[{
            'role': 'user',
            'content': (
                'Summarize the following text in one sentence.\n\n'
                'Text:\n' + documents.body
            ),
        }],
        model='gpt-4o-mini',
    ),
    if_exists='ignore',
)
documents.add_computed_column(
    summary=documents.doc_response['choices'][0]['message']['content'],
    if_exists='ignore',
)
