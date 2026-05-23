import React from 'react';
import { Box, Typography, Stepper, Step, StepLabel } from '@mui/material';

const RunTimelinePanel: React.FC = () => (
  <Box sx={{ p: 2 }}>
    <Typography variant="overline">Execution Timeline</Typography>
    <Stepper orientation="vertical" nonLinear>
      <Step active><StepLabel>Initialized</StepLabel></Step>
      <Step active><StepLabel>Thinking</StepLabel></Step>
      <Step><StepLabel>Tool Call (Pending)</StepLabel></Step>
    </Stepper>
  </Box>
);

export default RunTimelinePanel;
