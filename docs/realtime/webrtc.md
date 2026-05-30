# WebRTC Audio Support

O sistema suporta WebRTC para baixa latência em comunicações de voz.

## Configuração

```env
WEBRTC_AUDIO_ENABLED=true
```

## Signaling Flow

O Control Plane atua como o signaling server para WebRTC:

1. O cliente gera um **SDP Offer**.
2. O cliente envia o offer para `POST /v1/voice/webrtc/offer`.
3. O servidor processa o offer e retorna um **SDP Answer**.
4. O canal de mídia (ICE candidates) é estabelecido diretamente ou via TURN server.

## Vantagens do WebRTC

- **Latência Ultrabaixa**: Ideal para conversação natural.
- **Resiliência**: Melhor tratamento de jitter e perda de pacotes em comparação com WebSockets puro para áudio.
- **Qualidade**: Suporte a codecs modernos como Opus.
