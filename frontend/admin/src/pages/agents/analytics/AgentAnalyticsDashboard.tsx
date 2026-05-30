import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, Spin, Select, Typography, Alert } from 'antd';
import { CheckCircleOutlined, WarningOutlined, DollarOutlined, ExperimentOutlined } from '@ant-design/icons';

const { Title } = Typography;

const AgentAnalyticsDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);

  useEffect(() => {
    // Simulated fetch - in real life, call /api/v1/admin/agents/analytics/dashboard?days={days}
    setTimeout(() => {
      setData({
        run_metrics: { total_runs: 1250, success_rate: 0.94, status_distribution: { completed: 1175, failed: 75 } },
        financial_metrics: { total_cost_brl: 450.25, total_tokens: 1500000 },
        operational_metrics: { tool_failure_rate: 0.02, policy_denials_count: 12, eval_pass_rate: 0.88 }
      });
      setLoading(false);
    }, 1000);
  }, [days]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!data) return <Alert message="No analytics data available." type="info" />;

  return (
    <div style={{ padding: '24px' }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col><Title level={2}>Agentic Analytics</Title></Col>
        <Col>
          <Select defaultValue={7} onChange={(val) => setDays(val)} style={{ width: 150 }}>
            <Select.Option value={1}>Last 24 Hours</Select.Option>
            <Select.Option value={7}>Last 7 Days</Select.Option>
            <Select.Option value={30}>Last 30 Days</Select.Option>
          </Select>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic 
              title="Run Success Rate" 
              value={data.run_metrics.success_rate * 100} 
              precision={1}
              suffix="%"
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
            <Progress percent={data.run_metrics.success_rate * 100} showInfo={false} strokeColor="#52c41a" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="Total Cost (BRL)" 
              value={data.financial_metrics.total_cost_brl} 
              precision={2}
              prefix={<DollarOutlined />}
            />
            <div style={{ fontSize: '12px', color: '#8c8c8c', marginTop: '8px' }}>
              {data.financial_metrics.total_tokens.toLocaleString()} tokens consumed
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="Tool Failure Rate" 
              value={data.operational_metrics.tool_failure_rate * 100} 
              precision={2}
              suffix="%"
              prefix={<WarningOutlined style={{ color: '#ff4d4f' }} />}
            />
            <Progress percent={data.operational_metrics.tool_failure_rate * 100} showInfo={false} strokeColor="#ff4d4f" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="Eval Pass Rate" 
              value={data.operational_metrics.eval_pass_rate * 100} 
              precision={1}
              suffix="%"
              prefix={<ExperimentOutlined style={{ color: '#1890ff' }} />}
            />
            <Progress percent={data.operational_metrics.eval_pass_rate * 100} showInfo={false} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="Security & Compliance">
            <Row>
              <Col span={12}>
                <Statistic title="Policy Denials" value={data.operational_metrics.policy_denials_count} />
              </Col>
              <Col span={12}>
                <Statistic title="SLO Breaches" value={2} valueStyle={{ color: '#cf1322' }} />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Volume">
             <Statistic title="Total Runs Executed" value={data.run_metrics.total_runs} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AgentAnalyticsDashboard;
