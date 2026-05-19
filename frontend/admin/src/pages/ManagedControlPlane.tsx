import React, { useState, useEffect } from 'react';

const ManagedControlPlane: React.FC = () => {
  const [organizations, setOrganizations] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [appliances, setAppliances] = useState([]);

  // Mock fetching data for now
  useEffect(() => {
    // In a real implementation, this would call the API endpoints
    // fetch('/managed/organizations').then(...)
  }, []);

  return (
    <div className="managed-control-plane-container">
      <h1>Managed Control Plane (SaaS)</h1>
      
      <section className="admin-section">
        <h2>Organizations</h2>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Slug</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {organizations.map(org => (
              <tr key={org.id}>
                <td>{org.name}</td>
                <td>{org.slug}</td>
                <td>{org.status}</td>
                <td>
                  <button className="btn-small">Edit</button>
                </td>
              </tr>
            ))}
            {organizations.length === 0 && <tr><td colSpan={4}>No organizations found.</td></tr>}
          </tbody>
        </table>
        <button className="btn-primary">Create Organization</button>
      </section>

      <section className="admin-section">
        <h2>Remote Appliances</h2>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Workspace</th>
              <th>Version</th>
              <th>Health</th>
              <th>Status</th>
              <th>Last Heartbeat</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {appliances.map(app => (
              <tr key={app.id}>
                <td>{app.name}</td>
                <td>{app.workspace_name}</td>
                <td>{app.version}</td>
                <td>
                   <span className={`status-badge status-${app.health_status}`}>
                     {app.health_status}
                   </span>
                </td>
                <td>{app.status}</td>
                <td>{new Date(app.last_heartbeat_at).toLocaleString()}</td>
                <td>
                  <button className="btn-danger btn-small">Revoke</button>
                </td>
              </tr>
            ))}
            {appliances.length === 0 && <tr><td colSpan={7}>No appliances enrolled.</td></tr>}
          </tbody>
        </table>
      </section>
    </div>
  );
};

export default ManagedControlPlane;
