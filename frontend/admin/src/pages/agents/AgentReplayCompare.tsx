import React from 'react';
import { Box, Typography, Grid, Paper, List, ListItem, ListItemText } from '@mui/material';

export const AgentReplayCompare: React.FC = () => {
    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>Replay Comparative Analysis</Typography>
            <Grid container spacing={2}>
                <Grid item xs={6}>
                    <Paper sx={{ p: 2 }}>
                        <Typography variant="h6">Baseline (Run A)</Typography>
                        <List dense>
                            <ListItem><ListItemText primary="1. Model Call" secondary="Token: 120" /></ListItem>
                            <ListItem><ListItemText primary="2. Tool Call: search" secondary="Result: ok" /></ListItem>
                            <ListItem><ListItemText primary="3. Final Answer" /></ListItem>
                        </List>
                    </Paper>
                </Grid>
                <Grid item xs={6}>
                    <Paper sx={{ p: 2, border: '1px solid #1976d2' }}>
                        <Typography variant="h6">Candidate (Run B)</Typography>
                        <List dense>
                            <ListItem><ListItemText primary="1. Model Call" secondary="Token: 145" /></ListItem>
                            <ListItem sx={{ bgcolor: '#e6ffec' }}><ListItemText primary="2. Tool Call: billing.lookup" secondary="Added Step" /></ListItem>
                            <ListItem><ListItemText primary="3. Tool Call: search" /></ListItem>
                            <ListItem><ListItemText primary="4. Final Answer" /></ListItem>
                        </List>
                    </Paper>
                </Grid>
                <Grid item xs={12}>
                    <Paper sx={{ p: 2, mt: 2 }}>
                        <Typography variant="h6">Metrics Delta</Typography>
                        <Typography variant="body2">Cost: +$0.02</Typography>
                        <Typography variant="body2">Latency: +450ms</Typography>
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    );
};

export default AgentReplayCompare;
