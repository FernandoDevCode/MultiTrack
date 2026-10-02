# Transformers 5.18.0 — CLAP API inspection

- Distribuição inspecionada: wheel PyPI `transformers==5.18.0`, correspondente à tag pública `v5.18.0`.
- Arquivos inspecionados na `.venv`: `transformers/models/clap/modeling_clap.py` e `processing_clap.py`.
- Pergunta: quais APIs públicas e tipos de retorno devem ser usados pelo adapter local sem pipeline high-level?

Conclusões:

- `ClapProcessor.__call__` recebe áudio pelo argumento `audio=` e aceita `sampling_rate=48000`.
- `ClapModel.get_text_features()` e `get_audio_features()` retornam `BaseModelOutputWithPooling`; o embedding projetado fica em `.pooler_output`.
- A implementação 5.18.0 já normaliza o embedding projetado, mas o adapter normaliza novamente de forma explícita antes da similaridade cosseno.
- `from_pretrained()` expõe `local_files_only`; o adapter também fixa `trust_remote_code=False`, `weights_only=True` e `use_safetensors=False` porque o artefato aprovado é `pytorch_model.bin`.
- Nenhum internal foi copiado; a integração usa somente API pública atrás de adapter próprio.
