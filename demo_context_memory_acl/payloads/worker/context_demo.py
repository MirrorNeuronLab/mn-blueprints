"""Authenticated Markdown memory demonstrations; no model or token estimates."""
from contextlib import contextmanager
import json
import os
import uuid

import grpc
from mn_context_engine_sdk.evidence import EvidenceClient


@contextmanager
def clients(context):
    address = os.environ['MN_CONTEXT_ADDR']
    token = os.environ['MN_CONTEXT_AUTH_TOKEN']
    job = context.get('job_id') or os.environ['MN_JOB_ID']
    run = context.get('run_id') or os.environ['MN_RUN_ID']
    with grpc.insecure_channel(address) as channel:
        grpc.channel_ready_future(channel).result(timeout=5)
        def make(principal):
            return EvidenceClient(channel, job_id=job, run_id=run,
                principal=principal, auth_token=token, timeout=5)
        try:
            yield make('operator'), make('auditor')
        except grpc.RpcError as exc:
            raise RuntimeError(f'Membrane {exc.code().name}: {exc.details()}') from None


def run_acl_demo(context):
    private = 'PRIVATE_APPROVAL_' + uuid.uuid4().hex
    with clients(context) as (owner, auditor):
        owner.ingest_text('# shared\n\nPublic observation.', record_id='shared',
            namespace='run', event_id='shared', allow=['operator', 'auditor'])
        owner.ingest_text('# shared\n\n' + private, record_id='private',
            namespace='run', event_id='private', allow=['operator'])
        if private not in owner.read_complete('run:private')['text']:
            raise AssertionError('Restricted record was not stored')
        result = auditor.recall('shared')
        ids = [r['handle']['source_id'] for r in result['records']]
        if 'run:shared' not in ids:
            raise AssertionError('ACL check has no positive public visibility')
        if 'run:private' in ids or private in json.dumps(result):
            raise AssertionError('Private record leaked in retrieval or witness')
        try:
            auditor.read('run:private')
        except grpc.RpcError as exc:
            if exc.code() not in {grpc.StatusCode.NOT_FOUND, grpc.StatusCode.PERMISSION_DENIED}:
                raise
        else:
            raise AssertionError('Private direct read was allowed')
        return {'auditor_visible_ids': ids, 'private_hidden': True,
            'private_read_denied': True, 'public_visible': True,
            'contract': 'mn.context.text.v1'}


def run_compression_demo(context):
    # The historical ID is retained; v2 measures bounded exact evidence admission.
    budget = 2048
    bodies = {f'fact-{i}': f'# goal-1\n\nsource:fact-{i}\n\n' +
        ('Source-qualified runtime evidence remains unknown. ' * 30) for i in range(8)}
    with clients(context) as (owner, _):
        for identity, body in bodies.items():
            owner.ingest_text(body, record_id=identity, namespace='run',
                event_id=identity, allow=['operator'])
        compiled = owner.compile_evidence({'version': 'mn.context.evidence.v2',
            'task': 'goal-1 Preserve source-qualified runtime evidence.',
            'source_mode': 'markdown', 'lexical_only': True,
            'record_scope': ['run:' + identity for identity in bodies],
            'sources': [{'source_id': 'run:fact-0', 'required': True}],
            'context_budget_utf8_bytes': budget})
        items = [item for bundle in compiled['bundles'] for item in bundle['items']]
        selected = '\n'.join(item['content'] for item in items)
        selected_bytes = sum(len(item['content'].encode()) for item in items)
        if not items or not 0 < selected_bytes <= budget or 'goal-1' not in selected or 'source:fact-0' not in selected:
            raise AssertionError('Bounded admission lost its goal or required source')
        for item in items:
            handle = item['handle']
            canonical = owner.read_complete(handle['source_id'], revision=handle['record_revision'])
            # Evidence handles address the canonical file; read spans address its body.
            offset = canonical['body_offset']
            exact = owner.read(handle['source_id'], revision=handle['record_revision'],
                start_byte=handle['start_byte']-offset, end_byte=handle['end_byte']-offset)['text']
            if exact != item['content']:
                raise AssertionError('Admitted evidence differs from its exact citation')
        for identity, body in bodies.items():
            if owner.read_complete('run:' + identity)['text'] != body:
                raise AssertionError('Admission changed the complete stored source')
        return {'contract': 'mn.context.evidence.v2', 'admission_status': compiled['status'],
            'budget_bytes': budget, 'input_bytes': sum(len(b.encode()) for b in bodies.values()),
            'selected_bytes': selected_bytes, 'goal_preserved': True,
            'source_refs_preserved': True, 'exact_citations': True,
            'complete_sources_preserved': True, 'generation_calls': 0}
