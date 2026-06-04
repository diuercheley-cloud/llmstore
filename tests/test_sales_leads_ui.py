import os


def test_admin_dashboard_ui_sales_section():
    html_path = 'control_plane/app/static/admin/index.html'
    if not os.path.exists(html_path):
        # Fallback for different working dirs
        html_path = '../' + html_path
        
    assert os.path.exists(html_path)
    with open(html_path, 'r') as f:
        content = f.read()
        
    assert 'id="salesSection"' in content
    assert 'fetchLeads()' in content
    assert 'renderLeads(' in content
    assert 'id="leadsTable"' in content
    assert 'id="addLeadForm"' in content
