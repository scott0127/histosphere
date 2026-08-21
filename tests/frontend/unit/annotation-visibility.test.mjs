import { readFile } from 'node:fs/promises';

test('learner chat does not render annotation hover while admin dry-run keeps it', async () => {
  const learnerChat = await readFile('components/ChatScreen.vue', 'utf8');
  const adminPage = await readFile('pages/admin.vue', 'utf8');

  assert.equal(learnerChat.includes('<AnnotatedText'), false);
  assert.equal(learnerChat.includes(':annotations="message.annotations"'), false);
  assert.equal(adminPage.includes('<AnnotatedText'), true);
  assert.equal(adminPage.includes(':annotations="promptDryRun.annotations"'), true);
});
