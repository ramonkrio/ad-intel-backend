# Ad Intelligence Backend

Backend FastAPI + Playwright para scraping da Meta Ad Library.

## Deploy no Railway

1. Crie um novo projeto no [Railway](https://railway.app)
2. Conecte este repositório GitHub
3. O Railway detecta automaticamente via `railway.toml`
4. Após deploy, copie a URL gerada (ex: `https://ad-intel.up.railway.app`)

## Variáveis de ambiente

Nenhuma obrigatória. Opcional:
```
PORT=8000
```

## Endpoints

### `GET /health`
Verifica se o serviço está rodando.

### `POST /search`
Busca anúncios na Meta Ad Library.

**Body:**
```json
{
  "theme": "advocacia trabalhista",
  "country": "BR",
  "limit": 20
}
```

**Response:**
```json
{
  "theme": "advocacia trabalhista",
  "total": 15,
  "ads": [
    {
      "id": "scraped_0_...",
      "page_name": "Escritório Silva & Associados",
      "body": "Você foi demitido sem justa causa?...",
      "snapshot_url": "https://facebook.com/ads/library/...",
      "video_url": null,
      "image_url": "https://..."
    }
  ]
}
```

## Uso local

```bash
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium
uvicorn main:app --reload
```

## ⚠️ Avisos

- Scraping viola os Termos de Uso da Meta
- Pode ser bloqueado por CAPTCHA
- Instável se o Meta mudar o layout da página
- Use para fins de pesquisa e análise competitiva
