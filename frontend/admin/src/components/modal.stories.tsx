import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { AlertTriangle } from "lucide-react";
import { Button } from "./button";
import { Modal } from "./modal";
import { Input } from "./input";
import modalHistory from "../stories/history/modal.md?raw";

const meta = {
  component: Modal,
  tags: ["ai-generated", "autodocs"],
  args: {
    open: true,
    title: "Promover release",
    description: "Revise o impacto da promoção antes de confirmar a publicação para produção.",
    size: "md",
    tone: "default",
  },
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Modal reutilizável para fluxos críticos do painel, com portal para `document.body`, fechamento por overlay/ESC e footer composável.\n\n## Histórico de mudanças\n" +
          modalHistory,
      },
    },
  },
} satisfies Meta<typeof Modal>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {
  args: {
    open: true,
    onOpenChange: () => undefined,
  },
  render: (args) => {
    const [open, setOpen] = useState(true);
    return (
      <>
        <Button onClick={() => setOpen(true)}>Abrir modal</Button>
        <Modal
          {...args}
          open={open}
          onOpenChange={setOpen}
          footer={
            <div className="flex justify-end gap-3">
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancelar
              </Button>
              <Button variant="primary" onClick={() => setOpen(false)}>
                Confirmar
              </Button>
            </div>
          }
        >
          <div className="space-y-4">
            <Input label="Janela de manutenção" defaultValue="2026-05-25 22:00 UTC" />
            <Input label="Aprovador responsável" defaultValue="qa@seudominio.com" />
          </div>
        </Modal>
      </>
    );
  },
};

export const States: Story = {
  args: {
    open: true,
    onOpenChange: () => undefined,
  },
  parameters: {
    controls: { disable: true },
  },
  render: () => {
    const [open, setOpen] = useState(true);
    return (
      <Modal
        open={open}
        onOpenChange={setOpen}
        title="Ação destrutiva"
        description="Use este fluxo para documentar loading, erro e foco nas ações primárias."
        tone="danger"
        footer={
          <div className="grid gap-3 md:grid-cols-3">
            <Button variant="secondary">Hover</Button>
            <Button variant="destructive" isLoading>
              Loading
            </Button>
            <Button variant="destructive" className="ring-2 ring-primary ring-offset-2 ring-offset-background">
              Focus
            </Button>
          </div>
        }
      >
        <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive">
          <div className="flex items-center gap-2 font-bold">
            <AlertTriangle className="h-4 w-4" />
            Error
          </div>
          <p className="mt-1">O backend primário falhou na validação de readiness e bloqueou a promoção.</p>
          <p className="mt-3 text-muted-foreground">Estado disabled é representado pelas ações indisponíveis no footer.</p>
          <div className="mt-4">
            <Button variant="ghost" disabled>
              Disabled
            </Button>
          </div>
        </div>
      </Modal>
    );
  },
};

export const Variants: Story = {
  args: {
    open: true,
    onOpenChange: () => undefined,
  },
  parameters: {
    controls: { disable: true },
  },
  render: () => {
    const [open, setOpen] = useState(true);
    return (
      <Modal
        open={open}
        onOpenChange={setOpen}
        title="Comparativo de variantes"
        description="Mesmo conteúdo, tamanhos diferentes para tarefas curtas ou fluxos largos."
        size="lg"
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="outline">Rascunho</Button>
            <Button>Publicar</Button>
          </div>
        }
      >
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-secondary p-4 text-sm">`sm`: confirmação curta.</div>
          <div className="rounded-2xl bg-secondary p-4 text-sm">`md`: formulário padrão.</div>
          <div className="rounded-2xl bg-secondary p-4 text-sm">`lg`: comparação e revisão.</div>
        </div>
      </Modal>
    );
  },
};

export const Usage: Story = {
  args: {
    open: false,
    onOpenChange: () => undefined,
  },
  parameters: {
    docs: {
      source: {
        code: `import { Button } from "@/components/button";
import { Modal } from "@/components/modal";

<Modal
  open={isOpen}
  onOpenChange={setIsOpen}
  title="Confirmar rollback"
  description="O rollback irá restaurar a release estável anterior."
  footer={
    <div className="flex justify-end gap-3">
      <Button variant="ghost" onClick={() => setIsOpen(false)}>
        Cancelar
      </Button>
      <Button variant="destructive" isLoading={isRollingBack}>
        Executar rollback
      </Button>
    </div>
  }
>
  <p className="text-sm text-muted-foreground">Confira o impacto antes de prosseguir.</p>
</Modal>`,
      },
    },
  },
  render: () => <div className="text-sm text-muted-foreground">Veja o snippet de uso na aba Docs.</div>,
};
