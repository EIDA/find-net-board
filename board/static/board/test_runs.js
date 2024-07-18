document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[name="filter"]').forEach(radio => {
        radio.addEventListener('change', function() {
            let filter = document.querySelector('input[name="filter"]:checked').value;
            let options = {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: 'numeric',
                minute: 'numeric',
                hour12: true
            };
            fetch(`/board/tests/?datacenters=${filter}`)
                .then(response => response.json())
                .then(data => {
                    let tableBody = document.getElementById('test-runs-body');
                    tableBody.innerHTML = '';
                    data.unique_test_times.forEach(test_time => {
                        let row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${(new Date(test_time.test_time)).toLocaleString(undefined, options)}</td>
                            <td>${test_time.count}</td>
                            <td>${test_time.null_fdsn_net_percentage.toFixed(2)}</td>
                            <td>${test_time.null_xml_net_percentage.toFixed(2)}</td>
                            <td>${test_time.null_eidarout_net_percentage.toFixed(2)}</td>
                            <td>${test_time.true_page_percentage.toFixed(2)}</td>
                            <td>${test_time.true_license_percentage.toFixed(2)}</td>
                            <td>${test_time.true_xml_doi_match_percentage.toFixed(2)}</td>
                        `;
                        tableBody.appendChild(row);
                    });
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        });
    });
});
