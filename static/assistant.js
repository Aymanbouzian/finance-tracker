document.querySelectorAll('[data-question]').forEach((button) => {
  button.addEventListener('click', () => {
    const field = document.getElementById('id_question');
    field.value = button.dataset.question;
    field.focus();
  });
});
document.getElementById('assistant-form')?.addEventListener('submit', () => {
  const button = document.getElementById('assistant-submit');
  button.disabled = true;
  document.getElementById('assistant-progress').textContent = 'Thinking on your server…';
});
