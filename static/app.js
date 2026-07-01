document.getElementById('orderForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const topic = document.getElementById('topic').value;
  const length = document.getElementById('length').value;
  const tone = document.getElementById('tone').value;
  const priceId = document.getElementById('price_id').value;

  const resp = await fetch('/create-checkout', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({topic, length, tone, price_id: priceId})
  });
  const data = await resp.json();
  if (data.url) {
    window.location = data.url;
  } else {
    alert('Error: ' + (data.error || 'Try again'));
  }
});
