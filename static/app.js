const orderTypeInputs = Array.from(document.querySelectorAll('input[name="order_type"]'));
const priceField = document.querySelector('[data-price-field]');
const priceInput = priceField?.querySelector('input[name="price"]');

function syncPriceField() {
  const selectedOrderType = orderTypeInputs.find((input) => input.checked)?.value;
  const isLimit = selectedOrderType === 'LIMIT';

  if (!priceField || !priceInput) {
    return;
  }

  priceField.hidden = !isLimit;
  priceInput.required = isLimit;
  if (!isLimit) {
    priceInput.value = '';
  }
}

orderTypeInputs.forEach((input) => {
  input.addEventListener('change', syncPriceField);
});

syncPriceField();
