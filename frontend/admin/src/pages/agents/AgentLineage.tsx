import React from 'react';
import { Box, Typography, Paper, Stepper, Step, StepLabel } from '@mui/material';

export const AgentLineage: React.FC = () => {
    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>Agent Lineage</Typography>
            <Paper sx={{ p: 2 }}>
                <Stepper orientation="vertical">
                    <Step active>
                        <StepLabel>
                            <Typography variant="subtitle1">v1.2.1 - Promoted to production</Typography>
                            <Typography variant="caption">2026-05-22 10:00 - Approved by admin@company.com</Typography>
                        </StepLabel>
                    </Step>
                    <Step active>
                        <StepLabel>
                            <Typography variant="subtitle1">v1.2.0 - Eval Baseline Set</Typography>
                            <Typography variant="caption">2026-05-21 14:30 - Pass rate: 98%</Typography>
                        </StepLabel>
                    </Step>
                    <Step active>
                        <StepLabel>
                            <Typography variant="subtitle1">v1.1.0 - Policy Updated</Typography>
                            <Typography variant="caption">2026-05-20 09:00 - Added data_retention_policy</Typography>
                        </StepLabel>
                    </Step>
                </Stepper>
            </Paper>
        </Box>
    );
};

export default AgentLineage;
