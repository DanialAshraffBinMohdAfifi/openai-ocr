# Document Extractor

Receipt and business document extraction web app. A user uploads an image or PDF, the Flask backend sends the processed document to OpenAI GPT-5 mini, and the app returns a clean structured JSON payload for the detected document type.

## Phase 1 Features

- Receipt image/PDF upload: JPG, JPEG, PNG, WEBP, PDF
- Flask API with CORS for local development
- OpenAI GPT-5 mini vision extraction
- One-call document type classification and extraction
- Document-specific JSON schemas
- Temporary upload storage with cleanup
- Python validation for required fields and amount checks
- Token usage and estimated cost tracking
- Before/after image preview for preprocessing checks
- React + Vite frontend with drag-and-drop upload
- Document-specific result cards, item tables, validation warnings, copy JSON, and download JSON

Local OCR, local document classification, authentication, and database storage are intentionally out of scope for Phase 1.

## Phase 2 Option A: Simplified Document-Type-Specific Extraction

The backend uses one OpenAI call to inspect the uploaded document, classify its document type, and return only the matching simplified schema. Supported `document_type` values are:

- `receipt`
- `invoice`
- `payment_receipt`
- `delivery_order`
- `unknown`

The top-level extraction shape is always:

```json
{
  "document_type": "receipt",
  "data": {},
  "warnings": []
}
```

Phase 2 keeps only the most important accounting fields for each document type. This reduces prompt length, output JSON size, irrelevant null fields, and UI clutter. Removed fields such as vendor address, phone, service charge, discount, rounding, amount paid, shipping fee, driver details, and long descriptions can be added back later if needed.

Item amount rules are shared across receipt, invoice, and payment receipt extraction:

- `unit_price` is the unit price only when clearly visible.
- `line_total` is the row total or amount column.
- If a document only shows `Amount`, `Amount (RM)`, `Total`, or `Line Total`, the value goes in `line_total` and `unit_price` stays `null`.
- The backend does not calculate `unit_price = line_total / quantity`.

Example receipt payload:

```json
{
  "document_type": "receipt",
  "data": {
    "vendor_name": "RESTORAN NASI KUKUS WARISAN",
    "receipt_date": "2026-06-30",
    "receipt_number": "R-1001",
    "payment_method": "Card",
    "subtotal": 42.74,
    "tax_sst_amount": 2.44,
    "total_amount": 45.18,
    "currency": "MYR",
    "category": "restaurant",
    "items": []
  },
  "warnings": []
}
```

Example invoice payload:

```json
{
  "document_type": "invoice",
  "data": {
    "vendor_name": "ABC SUPPLIES SDN BHD",
    "customer_name": "XYZ ENGINEERING",
    "invoice_number": "INV-1001",
    "invoice_date": "2026-07-01",
    "due_date": null,
    "subtotal": 2264.15,
    "tax_sst_amount": 135.85,
    "total_amount": 2400.0,
    "currency": "MYR",
    "items": []
  },
  "warnings": []
}
```

Example payment receipt payload:

```json
{
  "document_type": "payment_receipt",
  "data": {
    "vendor_name": "ABC SUPPLIES SDN BHD",
    "payer_name": "XYZ ENGINEERING",
    "receipt_number": "OR-8821",
    "payment_date": "2026-07-02",
    "reference_number": null,
    "payment_method": "Bank transfer",
    "total_amount_received": 2400.0,
    "currency": "MYR",
    "items": []
  },
  "warnings": []
}
```

Example delivery order payload:

```json
{
  "document_type": "delivery_order",
  "data": {
    "vendor_name": "ABC SUPPLIES SDN BHD",
    "delivery_order_number": "DO-7788",
    "delivery_date": "2026-07-03",
    "customer_name": "XYZ ENGINEERING",
    "customer_po_number": null,
    "deliver_to": "XYZ ENGINEERING WAREHOUSE",
    "items": []
  },
  "warnings": []
}
```

Example unknown payload:

```json
{
  "document_type": "unknown",
  "data": {
    "visible_title": null,
    "detected_vendor_or_source": null,
    "detected_date": null,
    "detected_reference_number": null,
    "detected_total_amount": null,
    "currency": null
  },
  "warnings": ["Document type is unclear."]
}
```

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
OPENAI_PROMPT_MODE=compact
MAX_UPLOAD_MB=10
MAX_PDF_PAGES=1
PDF_RENDER_DPI=200
IMAGE_PREPROCESS_MODE=auto
AUTO_CROP_RECEIPT=true
SCANNER_CROP_MODE=conservative
MIN_CROP_CONFIDENCE=0.85
CROP_PADDING_RATIO=0.08
CROP_MIN_AREA_RATIO=0.50
CONSERVATIVE_CROP=true
ENABLE_PERSPECTIVE_CORRECTION=true
MAX_IMAGE_DIMENSION=1200
IMAGE_JPEG_QUALITY=80
RETURN_IMAGE_PREVIEW=true
SHOW_PREPROCESS_DEBUG=true
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

Document extraction:

```http
POST /api/extract
Content-Type: multipart/form-data
```

The file field name must be `file`.

Supported uploads are JPG, JPEG, PNG, WEBP, and PDF.

Item fields use these meanings:

- `items[].unit_price` is the unit price if a unit price or rate is clearly visible.
- `items[].unit_price` is `null` when the document only shows a row amount or line total.
- `items[].line_total` is the line total or row amount for the item.
- Quantity may be extracted from a quantity column or description text such as `(20 pcs)`.

## Example API Response

```json
{
  "success": true,
  "filename": "receipt.jpg",
  "data": {
    "document_type": "receipt",
    "data": {
      "vendor_name": "KAPTAN STATION",
      "receipt_date": "2026-07-12",
      "receipt_number": "C1-0238963",
      "total_amount": 57.9,
      "currency": "MYR",
      "items": [
        {
          "name": "ORANGE JUICE",
          "quantity": 1,
          "unit_price": 6.5,
          "line_total": 6.5
        }
      ]
    },
    "warnings": []
  },
  "validation": {
    "document_type": "receipt",
    "valid_for_document_type": true,
    "required_fields_check": true,
    "items_total_check": true,
    "total_breakdown_check": true,
    "warnings": []
  },
  "usage": {
    "model": "gpt-5-mini",
    "input_tokens": 2850,
    "output_tokens": 920,
    "total_tokens": 3770,
    "total_cost_usd": 0.002553,
    "total_cost_myr": 0.012
  },
  "image_preview": {
    "original_image_url": "data:image/jpeg;base64,...",
    "processed_image_url": "data:image/jpeg;base64,..."
  },
  "pdf": {
    "is_pdf": false
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

## Input Token Optimization

The backend uses compact prompt mode by default:

```env
OPENAI_PROMPT_MODE=compact
```

Compact mode keeps document type classification, document-specific schemas, and the critical extraction rules while removing long examples and repeated explanations from the text prompt. Use `OPENAI_PROMPT_MODE=normal` only when debugging extraction quality.

Default image processing is tuned for lower input token usage during testing:

```env
MAX_IMAGE_DIMENSION=1200
IMAGE_JPEG_QUALITY=80
MAX_PDF_PAGES=1
```

The OpenAI request sends the text prompt as text and each processed image only through the vision image input field. The backend does not put image previews, base64 data, crop metadata, token usage, previous JSON, or frontend response metadata into the text prompt.

In development mode, the backend logs safe request metadata only: model, prompt mode, prompt character length, processed image dimensions/format, number of images sent, and estimated payload size. It does not log API keys, full prompts, base64 image data, or extracted JSON.

The API response includes safe optimization metadata:

```json
{
  "optimization": {
    "prompt_mode": "compact",
    "schema_mode": "simplified_document_specific",
    "document_type": "receipt",
    "prompt_character_length": 1234,
    "image_max_dimension": 1200,
    "number_of_images_sent": 1
  }
}
```

To compare before and after, run the same document with the same model and compare `usage.input_tokens`, `usage.output_tokens`, and `usage.total_cost_*` in the Token Usage panel.

## Testing Cost Tracker

During local testing, the backend appends usage and cost metadata to:

```text
backend/logs/extraction_cost_log.csv
```

The log stores request metadata such as filename, file type, model, token usage, estimated USD/MYR cost, processing time, success status, and a safe error message for failed attempts. It does not store uploaded images, extracted JSON, API keys, or secrets.

Use these endpoints to inspect testing cost totals:

```text
GET /api/cost-summary
GET /api/cost-log?limit=50
DELETE /api/cost-log
```

The reset endpoint is intended for development/testing and is disabled when `FLASK_ENV=production`. Cost logs are ignored by git through `backend/logs/` and `*.csv`.

## Before/After Image Preview

The frontend shows the original uploaded document image and the processed image prepared for OpenAI. This helps debug preprocessing quality and confirm that document text is still readable before extraction.

The backend generates the processed image with Pillow by applying EXIF orientation correction, RGB conversion, max-dimension resizing, and JPEG compression. The processed image preview is the same data URL sent to OpenAI. Image previews are returned for display only and are not stored permanently.

To reduce response size, disable preview data in `backend/.env`:

```env
RETURN_IMAGE_PREVIEW=false
```

## PDF Support

PDF uploads are rendered into images using PyMuPDF. Rendered pages then pass through the same image preprocessing pipeline as normal image uploads, including automatic crop, adaptive preprocessing, resize, and JPEG compression.

By default, the backend renders only the first PDF page at 200 DPI:

```env
MAX_PDF_PAGES=1
PDF_RENDER_DPI=200
```

All processed PDF page images up to `MAX_PDF_PAGES` are sent to OpenAI in one request. The before/after preview shows the first rendered page and the processed version of that first page. If a PDF has more pages than `MAX_PDF_PAGES`, the response includes a warning in the `pdf.pdf_warnings` array.

PDF metadata is returned in the API response:

```json
{
  "pdf": {
    "is_pdf": true,
    "total_pdf_pages": 5,
    "processed_pdf_pages": 3,
    "pdf_render_dpi": 200,
    "pdf_warnings": [
      "PDF has 5 pages. Only first 3 pages were processed."
    ]
  }
}
```

Password-protected, corrupted, empty, or unrenderable PDFs return a clean error response instead of crashing Flask.

## Scanner-Style Crop and Adaptive Preprocessing

The backend uses a conservative CamScanner-style crop stage before preprocessing. It tries multiple OpenCV strategies to find the outer paper/document boundary:

- edge-based contour detection
- bright paper mask detection
- rectangular threshold contour detection
- fallback paper-colored region bounding box

Each candidate is scored from 0 to 1 using area coverage, rectangularity, corner count, aspect ratio, edge proximity, and top/bottom preservation. The default threshold is conservative:

```env
SCANNER_CROP_MODE=conservative
MIN_CROP_CONFIDENCE=0.85
CROP_PADDING_RATIO=0.08
CROP_MIN_AREA_RATIO=0.50
ENABLE_PERSPECTIVE_CORRECTION=true
```

If the best candidate is uncertain, too small, too centered, or likely to be an inner table/text block, the crop is rejected and the original image is used. This is intentional: for OCR, preserving vendor name, date, document number, totals, and footer is more important than a tight crop.

When a reliable four-corner outer document boundary is found, the backend may apply perspective correction. Otherwise it uses a padded rectangular crop or safely falls back to the original image.

After cropping, the backend generates preprocessing candidates internally:

- `original_color`
- `enhanced_color`
- `grayscale`
- `adaptive_threshold`

The system scores those candidates using simple sharpness, contrast, brightness, and black/white pixel balance checks, then automatically selects the safest best image. Users do not choose preprocessing modes. The processed image preview is the exact image data URL sent to OpenAI.

Debug metadata can be controlled with:

```env
SHOW_PREPROCESS_DEBUG=true
```

Set it to `false` in production if you want to hide candidate scores from the API response.

## Future Phases

Phase 2:
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
