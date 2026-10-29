# Documentos de referencia

Coloca aquí los PDFs, `.txt` o `.md` con las guías oficiales (DETRAN de cada
estado, consulados, portales gov.br, etc.) y luego ejecuta:

```bash
python scripts/ingest.py
```

- **Solo se commitea** este README (ver `.gitignore`). Los documentos reales
  quedan fuera del repositorio porque contienen precios, datos bancarios,
  contactos o datos personales.
- Para probar sin documentos reales, copia aquí `data/samples/ejemplo_guia_demo.md`.
- Las directrices de trato e idioma del agente NO van aquí, sino en
  `agent_core/prompts.py`: el modelo ignora instrucciones dentro de los
  documentos (protección contra prompt injection).
- El agente responde **únicamente** con lo que esté en estos archivos: la
  calidad de las respuestas depende directamente de la calidad y vigencia de
  los documentos que pongas aquí.
- Este README se ignora durante la ingesta.
