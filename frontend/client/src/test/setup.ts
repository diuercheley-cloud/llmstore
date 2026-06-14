import '@testing-library/jest-dom';

// Mock ResizeObserver which is used by Recharts
(globalThis as any).ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
};
