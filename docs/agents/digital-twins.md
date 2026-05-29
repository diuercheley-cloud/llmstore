# Digital Twins

## Overview
The Digital Twin subsystem provides a secure abstraction layer for AI agents to interact with physical and industrial assets. Each twin represents a real-world entity (e.g., a sensor, an industrial pump, or a smart building controller) and exposes its current state and authorized control commands.

## Architecture
- **Twin Registry**: Centralized management of digital twin definitions, connector types (MQTT, OPC-UA, Mock), and configurations.
- **Twin State**: Real-time tracking of observed data points from physical assets.
- **Twin Connector**: An extensible framework for bridging the gap between agent logic and industrial protocols.

## Control Flow
1. **Observation**: Agents read the latest state of a twin via the registry.
2. **Intent**: The agent issues a command (e.g., `adjust_temperature`).
3. **Safety Gate**: The `SafetyInterlock` service checks the command against physical safety boundaries and dangerous patterns.
4. **Approval**: High-risk actions or any actuation in production requires explicit human signature.
5. **Execution**: The command is dispatched via the connector, and a receipt is recorded in the immutable audit trail.

## Usage
Enable via `AGENT_DIGITAL_TWINS_ENABLED=true`.
Monitor safety events via `GET /admin/agents/digital-twins/safety-events`.
