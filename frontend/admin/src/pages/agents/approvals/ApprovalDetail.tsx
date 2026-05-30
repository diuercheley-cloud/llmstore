import React from 'react';
import { Card, Descriptions, Button, Space, Typography } from 'antd';

const { Title, Paragraph } = Typography;

const ApprovalDetail: React.FC<{ approval: any }> = ({ approval }) => {
  return (
    <Card title={`Approval Request: ${approval.id}`}>
      <Descriptions bordered column={1}>
        <Descriptions.Item label="Agent">{approval.agent_name}</Descriptions.Item>
        <Descriptions.Item label="Risk Level">
          <Tag color="red">{approval.risk_level}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Requested Reason">{approval.reason}</Descriptions.Item>
        <Descriptions.Item label="Tool to Execute">{approval.sanitized_context.tool_name}</Descriptions.Item>
        <Descriptions.Item label="Tool Input">
          <pre>{JSON.stringify(approval.sanitized_context.tool_input, null, 2)}</pre>
        </Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 24 }}>
        <Title level={4}>Decision</Title>
        <Space>
          <Button type="primary" size="large">Approve</Button>
          <Button danger size="large">Reject</Button>
          <Button size="large">Request Changes</Button>
        </Space>
      </div>
    </Card>
  );
};

export default ApprovalDetail;
