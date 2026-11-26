(() => {
  const data = JSON.parse(document.getElementById('chart-data').textContent);
  Chart.defaults.font.family = "'Segoe UI', Arial, sans-serif";
  Chart.defaults.font.size = 10;
  Chart.defaults.color = '#8c9888';
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  new Chart(document.getElementById('history'), {
    type: 'bar',
    data: {labels: data.history.labels.map(label => label.split(' ')[0]), datasets: [
      {label: 'Income', data: data.history.income, backgroundColor: '#285b43', borderRadius: 4, maxBarThickness: 18},
      {label: 'Expenses', data: data.history.expense, backgroundColor: '#c6d9a4', borderRadius: 4, maxBarThickness: 18}
    ]},
    options: {responsive: true, maintainAspectRatio: false, animation: !reduceMotion,
      plugins: {legend: {display: false}},
      scales: {x: {grid: {display: false}, border: {display: false}, ticks: {padding: 8}},
        y: {beginAtZero: true, border: {display: false}, grid: {color: '#f0f3ec'}, ticks: {maxTicksLimit: 5, callback: value => value >= 1000 ? `${value / 1000}k` : value}}}}
  });
  const categories = document.getElementById('categories');
  if (categories) new Chart(categories, {type: 'doughnut',
    data: {labels: data.categories.labels, datasets: [{data: data.categories.values,
      backgroundColor: ['#174e40','#78ae92','#bacf84','#e2ba78','#9b9fc5','#87bdc6','#ba9d8d','#a8b1b0'], borderWidth: 3, borderColor: '#fff', hoverOffset: 3}]},
    options: {responsive: true, maintainAspectRatio: false, cutout: '79%', animation: !reduceMotion, plugins: {legend: {display: false}}}
  });
})();
