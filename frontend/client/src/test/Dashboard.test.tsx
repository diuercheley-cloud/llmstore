import { render, screen, waitFor } from '@testing-library/react';
import { Dashboard } from '../components/Dashboard';
import { api } from '../lib/api';
import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../lib/api', () => ({
  api: {
    getPortalUsage: vi.fn(),
    getPortalUsageStats: vi.fn(),
  },
}));

describe('Dashboard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (api.getPortalUsage as any).mockReturnValue(new Promise(() => {}));
    (api.getPortalUsageStats as any).mockReturnValue(new Promise(() => {}));
    
    render(<Dashboard />);
    expect(screen.getByText(/Carregando dados do dashboard/i)).toBeInTheDocument();
  });

  it('renders usage data when API calls succeed', async () => {
    (api.getPortalUsage as any).mockResolvedValue({
      tokens_month: 50000,
      requests_month: 1200,
      customer_pricing: {
        currency: 'BRL',
        month_amount: 150.50
      }
    });
    
    (api.getPortalUsageStats as any).mockResolvedValue({
      daily_usage: [
        { day: '2026-06-12', tokens: 1000, requests: 20 },
        { day: '2026-06-13', tokens: 1500, requests: 30 }
      ]
    });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('50,000')).toBeInTheDocument();
      expect(screen.getByText('BRL 150.50')).toBeInTheDocument();
      expect(screen.getByText('1,200')).toBeInTheDocument();
    });
  });

  it('renders error state when API calls fail', async () => {
    (api.getPortalUsage as any).mockRejectedValue(new Error('API Error'));
    (api.getPortalUsageStats as any).mockResolvedValue({ daily_usage: [] });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Erro ao carregar Dashboard/i)).toBeInTheDocument();
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
  });
});
