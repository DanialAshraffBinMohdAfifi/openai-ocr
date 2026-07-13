# Receipt Extractor

Phase 1 receipt extraction web app. A user uploads a receipt image, the Flask backend sends the image to OpenAI GPT-5 mini, and the app returns a clean structured JSON receipt payload.

## Phase 1 Features

- Receipt image upload only: JPG, JPEG, PNG, WEBP
- Flask API with CORS for local development
- OpenAI GPT-5 mini vision extraction
- Strict JSON receipt schema
- Temporary upload storage with cleanup
- Python validation for required fields and amount checks
- Token usage and estimated cost tracking
- Before/after image preview for preprocessing checks
- React + Vite frontend with drag-and-drop upload
- Summary cards, item table, validation warnings, copy JSON, and download JSON

PDF support, local OCR, document classification, authentication, and database storage are intentionally out of scope for Phase 1.

## Folder Structure

```text
backend/
  app.py
  requirements.txt
  .env.example
  services/
    cost_service.py
    image_service.py
    openai_service.py
    validation_service.py
    file_service.py
  prompts/
    receipt_prompt.py
frontend/
  package.json
  vite.config.js
  index.html
  src/
    main.jsx
    App.jsx
    api.js
    components/
      UploadBox.jsx
      ImagePreview.jsx
      ResultViewer.jsx
      UsageCostPanel.jsx
      JsonViewer.jsx
      OcrTextBox.jsx
    styles.css
README.md
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5-mini
MAX_UPLOAD_MB=10
MAX_IMAGE_DIMENSION=1600
IMAGE_JPEG_QUALITY=85
RETURN_IMAGE_PREVIEW=true
FLASK_ENV=development

OPENAI_INPUT_COST_PER_1M=0.25
OPENAI_OUTPUT_COST_PER_1M=2.00
USD_TO_MYR_RATE=4.70
```

Run the backend:

```bash
python app.py
```

The API runs at `http://localhost:5000`.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`.

## API

Health check:

```http
GET /api/health
```

Receipt extraction:

```http
POST /api/extract
Content-Type: multipart/form-data
```

The file field name must be `file`.

## Example API Response

```json
{
  "success": true,
  "filename": "receipt.jpg",
  "data": {
    "vendor_name": "KAPTAN STATION",
    "receipt_date": "2026-07-12",
    "receipt_number": "C1-0238963",
    "reference_number": null,
    "total_amount": 57.9,
    "tax_sst_amount": 3.28,
    "short_description": "Restaurant receipt from KAPTAN STATION with multiple food and drink items.",
    "currency": "MYR",
    "items": [
      {
        "name": "ORANGE JUICE",
        "quantity": 1,
        "amount": 6.5,
        "total": 6.5
      }
    ],
    "warnings": []
  },
  "validation": {
    "has_vendor_name": true,
    "has_receipt_date": true,
    "has_receipt_or_reference_number": true,
    "has_total_amount": true,
    "items_total_check": true,
    "warnings": []
  },
  "usage": {
    "model": "gpt-5-mini",
    "input_tokens": 2850,
    "output_tokens": 920,
    "total_tokens": 3770,
    "input_cost_usd": 0.000713,
    "output_cost_usd": 0.00184,
    "total_cost_usd": 0.002553,
    "total_cost_myr": 0.012,
    "pricing": {
      "input_per_1m_usd": 0.25,
      "output_per_1m_usd": 2.0,
      "usd_to_myr_rate": 4.7
    }
  },
  "image_preview": {
    "original_image_url": "data:image/jpeg;base64,...",
    "processed_image_url": "data:image/jpeg;base64,...",
    "metadata": {
      "original_width": 810,
      "original_height": 1080,
      "processed_width": 810,
      "processed_height": 1080,
      "processed_format": "JPEG",
      "jpeg_quality": 85,
      "max_dimension": 1600
    }
  },
  "processing_time_ms": 1234
}
```

## Token Usage & Cost Tracking

The backend reads token usage from the OpenAI API response when it is available and returns it in the `usage` object. Cost estimates are calculated in the backend using configurable pricing values from `backend/.env`.

Default GPT-5 mini pricing is:

```env
OPENAI_INPUT_COST_PER_1M=0.25
OPENAI_OUTPUT_COST_PER_1M=2.00
USD_TO_MYR_RATE=4.70
```

The frontend only displays the usage and cost data returned by the backend. Estimated cost may differ slightly from actual billing, and the USD to MYR exchange rate is manually configured.

## Before/After Image Preview

The frontend shows the original uploaded receipt image and the processed image prepared for OpenAI. This helps debug preprocessing quality and confirm that receipt text is still readable before extraction.

The backend generates the processed image with Pillow by applying EXIF orientation correction, RGB conversion, max-dimension resizing, and JPEG compression. The processed image preview is the same data URL sent to OpenAI. Image previews are returned for display only and are not stored permanently.

To reduce response size, disable preview data in `backend/.env`:

```env
RETURN_IMAGE_PREVIEW=false
```

## Future Phases

Phase 2:
- Add PDF support using PyMuPDF
- Add image preprocessing with OpenCV
- Add upload preview

Phase 3:
- Add local OCR helper using PaddleOCR or EasyOCR
- Send rough OCR text together with image to OpenAI

Phase 4:
- Add local classifier for document type routing

Phase 5:
- Add GPT-5 nano cheap path and GPT-5 mini fallback
- Add batch processing
- Add database storage
