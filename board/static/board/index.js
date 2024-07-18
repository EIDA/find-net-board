document.getElementById('search-form').addEventListener('submit', function(event) {
  event.preventDefault();
  let datacenterFilter = document.querySelector('input[name="datacenter-filter"]:checked').value;
  let networkCode = document.getElementById('search-network').value.toUpperCase();
  let startDate = document.getElementById('start-date').value;
  let endDate = document.getElementById('end-date').value;
  let options = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      hour12: true
  };

  fetch(`/board/search_tests/?datacenters=${datacenterFilter}&network=${networkCode}&start=${startDate}&end=${endDate}`)
      .then(response => response.json())
      .then(data => {
          // Clear existing table rows
          let tableBody = document.querySelector('#tests-table tbody');
          tableBody.innerHTML = '';

          // Populate table with new data
          data.tests.forEach(test => {
              let row = document.createElement('tr');
              row.innerHTML = `
                  <td>${(new Date(test.test_time)).toLocaleString(undefined, options)}</td>
                  <td>${test.datacenter}</td>
                  <td>${test.network_code}</td>
                  <td>${test.start_date}</td>
                  <td>${test.doi ? `<a href="https://doi.org/${test.doi}">${test.doi}</a>` : '-'}</td>
                  <td>${test.fdsn_net ? '✅' : '❌'}</td>
                  <td>${test.xml_net ? '✅' : '❌'}</td>
                  <td>${test.eidarout_net ? '✅' : '❌'}</td>
                  <td>${test.page_works !== null ? (test.page_works ? '✅' : '❌') : '-'}</td>
                  <td>${test.has_license !== null ? (test.has_license ? '✅' : '❌') : '-'}</td>
                  <td>${test.xml_doi_match !== null ? (test.xml_doi_match ? '✅' : '❌') : '-'}</td>
              `;
              tableBody.appendChild(row);
          });
      })
      .catch(error => {
          console.error('Error:', error);
      });
});
