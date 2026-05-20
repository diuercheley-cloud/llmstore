import type { Meta, StoryObj } from "@storybook/react-vite";
import { Search, Eye } from "lucide-react";
import { Input } from "./input";
import inputHistory from "../stories/history/input.md?raw";

const meta = {
  component: Input,
  tags: ["ai-generated", "autodocs"],
  args: {
    label: "Nome do ambiente",
    placeholder: "production-sa-east-1",
    hint: "Use um identificador curto e legível.",
    size: "md",
    disabled: false,
  },
  parameters: {
    docs: {
      description: {
        component:
          "Campo de entrada reutilizável com suporte a rótulo, ajuda contextual, mensagem de erro e adornos visuais.\n\n## Histórico de mudanças\n" +
          inputHistory,
      },
    },
  },
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const States: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="grid w-[760px] gap-5 md:grid-cols-2">
      <Input label="Default" placeholder="search clusters" leadingIcon={<Search className="h-4 w-4" />} />
      <Input
        label="Hover"
        placeholder="hover state"
        className="border-primary/50 shadow-lg shadow-primary/10"
        leadingIcon={<Search className="h-4 w-4" />}
      />
      <Input label="Loading" placeholder="saving..." trailingAddon={<span className="text-xs">...</span>} />
      <Input label="Disabled" placeholder="disabled field" disabled />
      <Input label="Error" placeholder="production-us-east" error="Identificador já está em uso." />
      <Input
        label="Focus"
        placeholder="focus-visible ring"
        className="ring-2 ring-primary ring-offset-2 ring-offset-background"
        trailingAddon={<Eye className="h-4 w-4" />}
      />
    </div>
  ),
};

export const Variants: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="space-y-4">
      <Input size="sm" label="Small" placeholder="api key alias" />
      <Input size="md" label="Medium" placeholder="api key alias" />
      <Input size="lg" label="Large" placeholder="api key alias" />
    </div>
  ),
};

export const Usage: Story = {
  parameters: {
    docs: {
      source: {
        code: `import { Search } from "lucide-react";
import { Input } from "@/components/input";

<Input
  label="Filtrar backends"
  placeholder="Buscar por nome ou região"
  leadingIcon={<Search className="h-4 w-4" />}
  hint="Busca local aplicada à tabela."
/>`,
      },
    },
  },
  render: () => (
    <Input
      label="Filtrar backends"
      placeholder="Buscar por nome ou região"
      leadingIcon={<Search className="h-4 w-4" />}
      hint="Busca local aplicada à tabela."
    />
  ),
};
