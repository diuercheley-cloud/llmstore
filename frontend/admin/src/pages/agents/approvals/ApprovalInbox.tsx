import React, { useState, useEffect } from 'react';
import { Table, Tag, Space, Button, Input, Select } from 'antd';

const ApprovalInbox: React.FC = () => {
  const [approvals, setApprovals] = useState([]);
  const [filter, setFilter] = useState({ risk: 'all', tenant: '' });

  return (
    <div className="approval-inbox">
      <h1>HITL Approval Inbox</h1>
      <Space style={{ marginBottom: 16 }}>
        <Select defaultValue="all" onChange={(val) => setFilter({...filter, risk: val})}>
          <Select.Option value="all">All Risks</Select.Option>
          <Select.Option value="low">Low</Select.Option>
          <Select.Option value="medium">Medium</Select.Option>
          <Select.Option value="high">High</Select.Option>
          <Select.Option value="critical">Critical</Select.Option>
        </Select>
        <Input placeholder="Filter by Tenant" onChange={(e) => setFilter({...filter, tenant: e.target.value})} />
      </Space>

      <Table 
        dataSource={approvals} 
        columns={[
          { title: 'ID', dataIndex: 'id', key: 'id' },
          { title: 'Agent', dataIndex: 'agent_name', key: 'agent' },
          { title: 'Risk', dataIndex: 'risk_level', key: 'risk', render: (risk) => <Tag color={risk === 'critical' ? 'red' : 'blue'}>{risk}</Tag> },
          { title: 'Reason', dataIndex: 'reason', key: 'reason' },
          { title: 'Expires', dataIndex: 'expires_at', key: 'expires' },
          { title: 'Actions', key: 'actions', render: (_, record: any) => (
            <Space>
              <Button type="primary">Review</Button>
              <Button danger>Reject</Button>
            </Space>
          )}
        ]}
      />
    </div>
  );
};

export default ApprovalInbox;
