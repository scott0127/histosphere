import assert from 'node:assert/strict';
import {
  sampleCondition,
  samplePersona,
} from '../fixtures/histosphereFixtures.mjs';

const conversationSession = await globalThis.loadTsModule('composables/useConversationSession.ts');

test('pending assistant identity never exposes persona in non-roleplay conditions', () => {
  const identity = conversationSession.resolvePendingAssistantIdentity(
    {
      ...sampleCondition,
      condition_key: 'no_ebl_no_roleplay',
      roleplay_enabled: false,
    },
    [samplePersona],
    [],
  );

  assert.deepEqual(identity, {
    speakerType: 'assistant',
    speakerName: 'AI Assistant',
    personaId: undefined,
  });
});

test('pending assistant identity uses the fixed persona in roleplay conditions', () => {
  const identity = conversationSession.resolvePendingAssistantIdentity(
    sampleCondition,
    [samplePersona],
    [],
  );

  assert.deepEqual(identity, {
    speakerType: 'persona',
    speakerName: samplePersona.name,
    personaId: samplePersona.id,
  });
});
