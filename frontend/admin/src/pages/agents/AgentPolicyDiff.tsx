import React from 'react';
import { Box, Typography, Paper, Divider } from '@mui/material';

export const AgentPolicyDiff: React.FC = () => {
    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>Agent Policy Diff</Typography>
            <Paper sx={{ p: 2 }}>
                <Typography variant="h6">Instructions Diff</Typography>
                <Box sx={{ bgcolor: '#ffeef0', p: 1, my: 1 }}>
                    <Typography variant="body2" sx={{ textDecoration: 'line-through' }}>- You are a helpful assistant.</Typography>
                </Box>
                <Box sx={{ bgcolor: '#e6ffec', p: 1, my: 1 }}>
                    <Typography variant="body2">+ You are a specialized customer support agent for billing inquiries.</Typography>
                </Box>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6">Tools Changed</Typography>
                <Typography variant="body2">Added: <code>billing.refund</code>, <code>billing.lookup</code></Typography>
                <Typography variant="body2">Removed: <code>general.search</code></Typography>
            </Paper>
        </Box>
    );
};

export default AgentPolicyDiff;
