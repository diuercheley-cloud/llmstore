import os

def test_ui_contains_control_center():
    ui_path = "control_plane/app/static/admin/index.html"
    assert os.path.exists(ui_path)
    
    with open(ui_path, 'r') as f:
        content = f.read()
        
    assert "System Control Center" in content
    assert "systemControlCenterSection" in content
    assert "renderControlCenter" in content
    assert "/admin/system/control-center" in content
    assert "cc-health" in content
    assert "cc-readiness" in content
    assert "cc-security" in content
    assert "suggestedCommands" in content
