import React from 'react';
import { Box, Typography, Paper, Button, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

export const AgentPromotion: React.FC = () => {
    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>Agent Promotion</Typography>
            <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Target: production</Typography>
                <List>
                    <ListItem>
                        <ListItemIcon><CheckCircleIcon color="success" /></ListItemIcon>
                        <ListItemText primary="Evaluation Results" secondary="Latest pass rate: 98% (Goal: 95%)" />
                    </ListItem>
                    <ListItem>
                        <ListItemIcon><CheckCircleIcon color="success" /></ListItemIcon>
                        <ListItemText primary="Human Approval" secondary="Approved by security-lead@company.com" />
                    </ListItem>
                    <ListItem>
                        <ListItemIcon><ErrorIcon color="error" /></ListItemIcon>
                        <ListItemText primary="Active Incidents" secondary="1 open critical incident detected" />
                    </ListItem>
                </List>
                <Button variant="contained" color="primary" disabled sx={{ mt: 2 }}>
                    Promote to Production
                </Button>
                <Typography variant="caption" display="block" sx={{ mt: 1, color: 'error.main' }}>
                    Promotion blocked due to active critical incidents.
                </Typography>
            </Paper>
        </Box>
    );
};

export default AgentPromotion;
