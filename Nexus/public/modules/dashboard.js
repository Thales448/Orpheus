// dashboard.js
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.querySelector('.refresh-btn');
  if (btn) {
    btn.addEventListener('click', () => {
      console.log('Refresh button clickedddddddddd');
      window.bulkLogsWorkloads?.(); // use optional chaining in case it's not defined yet
    });
  }
});
