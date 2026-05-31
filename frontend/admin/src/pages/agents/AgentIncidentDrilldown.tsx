import React from 'react';
import { Box, Typography, Paper, Chip } from '@mui/material';

export const AgentIncidentDrilldown: React.FC = () => {
    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>Incident Drill-down</Typography>
            <Paper sx={{ p: 2, mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Typography variant="h6">handoff_loop detected</Typography>
                    <Chip label="High Severity" color="error" size="small" />
                </Box>
                <Typography variant="body2" color="text.secondary">Run ID: 123e4567-e89b-12d3-a456-426614174000</Typography>
                <Typography variant="body1" sx={{ mt: 2 }}>
                    The agent entered a recursive handoff loop between 'BillingAgent' and 'SupportAgent' after failing to resolve the refund query.
                </Typography>
            </Paper>
            <Paper sx={{ p: 2 }}>
                <Typography variant="h6">Related Traces</Typography>
                <Typography variant="body2">Trace 1: handoff.started -&gt; BillingAgent</Typography>
                <Typography variant="body2">Trace 2: handoff.started -&gt; SupportAgent</Typography>
                <Typography variant="body2">Trace 3: handoff.started -&gt; BillingAgent</Typography>
            </Paper>
        </Box>
    );
};

export default AgentIncidentDrilldown;
