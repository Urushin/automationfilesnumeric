"""
SSE Streaming Pipeline Router — v3.0
Runs the full Etsy Laser Automation pipeline step by step and streams
real-time progress events to the frontend via Server-Sent Events.
with open(transcript_path, "r", encoding="utf-8") as f:
Changements v3.0 :
- session_token pour la recovery côté client
- Export .ai et .eps intégrés (Step 3)
- Détection d'îles SVG (Step 2)
- Compliance check Etsy (Step 6)
- description_en sauvegardée en DB
- ZIP inclut SVG + DXF + AI + EPS + PDF + PNG
"""
import asyncio
import json
import os
import shutil
from datetime import datetime
from typing import AsyncGenerator
                    match = line_pattern.match(l.strip())
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
                        reconstructed_lines[line_num] = line_code
from ..database import get_db, SessionLocal
from ..models import Creation
from ..routers.settings import get_or_create_settings
from ..services.dalle_image import generate_stencil_image
from ..services.gemini_seo import generate_etsy_seo
from ..services.generator import generate_seo_metadata
from ..services.vector import png_to_svg, svg_to_dxf
from ..services.image import convert_to_transparent_png, package_assets, png_to_pdf
from ..services.mockup_processor import create_ecommerce_mockup
from ..services.export_formats import svg_to_ai, svg_to_eps, svg_to_high_quality_png
from ..services.svg_analyzer import analyze_svg_connectivity
from ..services.compliance import run_compliance_check
from ..services.compliance import run_compliance_check
router = APIRouter(prefix="/api/pipeline", tags=["Pipeline SSE"])
router = APIRouter(prefix="/api/pipeline", tags=["Pipeline SSE"])
STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../storage")
)
os.makedirs(STORAGE_DIR, exist_ok=True)
./backend/app/routers/creations.py
./backend/app/routers/health.py
# ─────────────────────────────────────────────────────────────────────────────
# SSE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
./backend/app/database.py
./backend/app/__init__.py
./backend/app/schemas.py
./backend/app/main.py
./backend/app/services
./backend/app/services/etsy_api.py
./backend/app/services/dalle_image.py
./backend/app/services/scraper.py
./backend/app/services/vector.py
./backend/app/services/export_formats.py
./backend/app/services/compliance.py
./backend/app/services/svg_analyzer.py
./backend/app/services/gemini_seo.py
./backend/app/services/generator.py
./backend/app/services/mockup_processor.py
./backend/app/services/image.py
./backend/requirements.txt
./backend/tests
./backend/tests/test_app.py
./backend/assets
./backend/assets/backgrounds
./backend/etsy_laser_auto.db
./project_structure.txt
./README.md
./etsy_laser_auto.db
# MISSING LINE 76

# MISSING LINE 77

# MISSING LINE 78

# MISSING LINE 79

# MISSING LINE 80

# MISSING LINE 81

# MISSING LINE 82

# MISSING LINE 83

# MISSING LINE 84

# MISSING LINE 85

# MISSING LINE 86

  - Capture the selected mockup styles array from `PipelineForm` and forward them in the SSE modular stream request query string.
# MISSING LINE 88

---
# MISSING LINE 90

#### [MODIFY] [page.tsx](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/frontend/app/review/%5Bid%5D/page.tsx)
- **Mandate 8 (Masonry/Grid UI & Checkbox overlays):**
  - Redesign the image review section as a clean, responsive Grid.
  - Add a checklist overlay on each asset card (mockups and split elements) to toggle their selection.
  - Add a "Select All / Deselect All" toggle.
  - In `handlePublish`, transmit the list of selected asset paths in the POST body to `/publish`.
- **Mandate 9 (Translation Trigger Button):**
  - Add a "Translate & Optimize to English" button next to French inputs that hits the backend translation route and updates the English text fields.
# MISSING LINE 99

---
# MISSING LINE 101

#### [NEW] [page.tsx](file:///Users/issam/Documents/Projets%20perso/AutomatisationNumericFiles/frontend/app/settings/prompts/page.tsx)
- **Mandate 11 (Prompt Dashboard UI):**
  - Implement a settings page that fetches and lists all system prompts with a copy-to-clipboard button.
# MISSING LINE 105

## Verification Plan
# MISSING LINE 107

### Automated Tests
- Run backend lint and compile checks: `python -m py_compile backend/app/services/image_engine.py` etc.
- Run frontend typechecks and build: `npm run build` inside `frontend`.
# MISSING LINE 111

### Manual Verification
- Test inpainting and verify that `mask_*.png` is deleted from backend workspace directory.
- Verify multi-style mockups are generated and named as `_mockup_commercial_[index].jpg`.
- Verify the Pan, Zoom, and Hand tools in the retouch canvas modal.
- Verify the Exclusion brush hides painted areas in the binarized/split output.
- Check that the Prompts page displays all prompts and copies to clipboard successfully.
# MISSING LINE 118

# MISSING LINE 119

# MISSING LINE 120

# MISSING LINE 121

# MISSING LINE 122

# MISSING LINE 123

# MISSING LINE 124

# MISSING LINE 125

# MISSING LINE 126

# MISSING LINE 127

# MISSING LINE 128

# MISSING LINE 129

# MISSING LINE 130

# MISSING LINE 131

# MISSING LINE 132

# MISSING LINE 133

# MISSING LINE 134

# MISSING LINE 135

# MISSING LINE 136

# MISSING LINE 137

# MISSING LINE 138

# MISSING LINE 139

# MISSING LINE 140

# MISSING LINE 141

# MISSING LINE 142

# MISSING LINE 143

# MISSING LINE 144

# MISSING LINE 145

# MISSING LINE 146

# MISSING LINE 147

# MISSING LINE 148

# MISSING LINE 149

# MISSING LINE 150

# MISSING LINE 151

# MISSING LINE 152

# MISSING LINE 153

# MISSING LINE 154

# MISSING LINE 155

# MISSING LINE 156

# MISSING LINE 157

# MISSING LINE 158

# MISSING LINE 159

# MISSING LINE 160

# MISSING LINE 161

# MISSING LINE 162

# MISSING LINE 163

# MISSING LINE 164

# MISSING LINE 165

# MISSING LINE 166

# MISSING LINE 167

# MISSING LINE 168

# MISSING LINE 169

# MISSING LINE 170

# MISSING LINE 171

# MISSING LINE 172

# MISSING LINE 173

# MISSING LINE 174

# MISSING LINE 175

# MISSING LINE 176

# MISSING LINE 177

# MISSING LINE 178

# MISSING LINE 179

# MISSING LINE 180

# MISSING LINE 181

# MISSING LINE 182

# MISSING LINE 183

# MISSING LINE 184

# MISSING LINE 185

# MISSING LINE 186

# MISSING LINE 187

# MISSING LINE 188

# MISSING LINE 189

# MISSING LINE 190

# MISSING LINE 191

# MISSING LINE 192

# MISSING LINE 193

# MISSING LINE 194

# MISSING LINE 195

# MISSING LINE 196

# MISSING LINE 197

# MISSING LINE 198

# MISSING LINE 199

# MISSING LINE 200

# MISSING LINE 201

# MISSING LINE 202

# MISSING LINE 203

# MISSING LINE 204

# MISSING LINE 205

# MISSING LINE 206

# MISSING LINE 207

# MISSING LINE 208

# MISSING LINE 209

# MISSING LINE 210

# MISSING LINE 211

# MISSING LINE 212

# MISSING LINE 213

# MISSING LINE 214

# MISSING LINE 215

# MISSING LINE 216

# MISSING LINE 217

# MISSING LINE 218

# MISSING LINE 219

# MISSING LINE 220

# MISSING LINE 221

# MISSING LINE 222

# MISSING LINE 223

# MISSING LINE 224

# MISSING LINE 225

# MISSING LINE 226

# MISSING LINE 227

# MISSING LINE 228

# MISSING LINE 229

# MISSING LINE 230

# MISSING LINE 231

# MISSING LINE 232

# MISSING LINE 233

# MISSING LINE 234

# MISSING LINE 235

# MISSING LINE 236

# MISSING LINE 237

# MISSING LINE 238

# MISSING LINE 239

# MISSING LINE 240

# MISSING LINE 241

# MISSING LINE 242

# MISSING LINE 243

# MISSING LINE 244

# MISSING LINE 245

# MISSING LINE 246

# MISSING LINE 247

# MISSING LINE 248

# MISSING LINE 249

# MISSING LINE 250

# MISSING LINE 251

# MISSING LINE 252

# MISSING LINE 253

# MISSING LINE 254

# MISSING LINE 255

# MISSING LINE 256

# MISSING LINE 257

# MISSING LINE 258

# MISSING LINE 259

# MISSING LINE 260

# MISSING LINE 261

# MISSING LINE 262

# MISSING LINE 263

# MISSING LINE 264

# MISSING LINE 265

# MISSING LINE 266

# MISSING LINE 267

# MISSING LINE 268

# MISSING LINE 269

# MISSING LINE 270

# MISSING LINE 271

# MISSING LINE 272

# MISSING LINE 273

# MISSING LINE 274

# MISSING LINE 275

# MISSING LINE 276

# MISSING LINE 277

# MISSING LINE 278

# MISSING LINE 279

# MISSING LINE 280

# MISSING LINE 281

# MISSING LINE 282

# MISSING LINE 283

# MISSING LINE 284

# MISSING LINE 285

# MISSING LINE 286

# MISSING LINE 287

# MISSING LINE 288

# MISSING LINE 289

# MISSING LINE 290

# MISSING LINE 291

# MISSING LINE 292

# MISSING LINE 293

# MISSING LINE 294

# MISSING LINE 295

# MISSING LINE 296

# MISSING LINE 297

# MISSING LINE 298

# MISSING LINE 299

# MISSING LINE 300

# MISSING LINE 301

# MISSING LINE 302

# MISSING LINE 303

# MISSING LINE 304

# MISSING LINE 305

# MISSING LINE 306

# MISSING LINE 307

# MISSING LINE 308

# MISSING LINE 309

# MISSING LINE 310

# MISSING LINE 311

# MISSING LINE 312

# MISSING LINE 313

# MISSING LINE 314

# MISSING LINE 315

# MISSING LINE 316

# MISSING LINE 317

# MISSING LINE 318

# MISSING LINE 319

# MISSING LINE 320

# MISSING LINE 321

# MISSING LINE 322

# MISSING LINE 323

# MISSING LINE 324

# MISSING LINE 325

# MISSING LINE 326

# MISSING LINE 327

# MISSING LINE 328

# MISSING LINE 329

# MISSING LINE 330

# MISSING LINE 331

# MISSING LINE 332

# MISSING LINE 333

# MISSING LINE 334

# MISSING LINE 335

# MISSING LINE 336

# MISSING LINE 337

# MISSING LINE 338

# MISSING LINE 339

# MISSING LINE 340

# MISSING LINE 341

# MISSING LINE 342

# MISSING LINE 343

# MISSING LINE 344

# MISSING LINE 345

# MISSING LINE 346

# MISSING LINE 347

# MISSING LINE 348

# MISSING LINE 349

# MISSING LINE 350

# MISSING LINE 351

# MISSING LINE 352

# MISSING LINE 353

# MISSING LINE 354

# MISSING LINE 355

# MISSING LINE 356

# MISSING LINE 357

# MISSING LINE 358

# MISSING LINE 359

# MISSING LINE 360

# MISSING LINE 361

# MISSING LINE 362

# MISSING LINE 363

# MISSING LINE 364

# MISSING LINE 365

# MISSING LINE 366

# MISSING LINE 367

# MISSING LINE 368

# MISSING LINE 369

# MISSING LINE 370

# MISSING LINE 371

# MISSING LINE 372

# MISSING LINE 373

# MISSING LINE 374

# MISSING LINE 375

# MISSING LINE 376

# MISSING LINE 377

# MISSING LINE 378

# MISSING LINE 379

# MISSING LINE 380

# MISSING LINE 381

# MISSING LINE 382

# MISSING LINE 383

# MISSING LINE 384

# MISSING LINE 385

# MISSING LINE 386

# MISSING LINE 387

# MISSING LINE 388

# MISSING LINE 389

# MISSING LINE 390

# MISSING LINE 391

# MISSING LINE 392

# MISSING LINE 393

# MISSING LINE 394

# MISSING LINE 395

# MISSING LINE 396

# MISSING LINE 397

# MISSING LINE 398

# MISSING LINE 399

# MISSING LINE 400

# MISSING LINE 401

# MISSING LINE 402

# MISSING LINE 403

# MISSING LINE 404

# MISSING LINE 405

# MISSING LINE 406

# MISSING LINE 407

# MISSING LINE 408

# MISSING LINE 409

# MISSING LINE 410

# MISSING LINE 411

# MISSING LINE 412

# MISSING LINE 413

# MISSING LINE 414

# MISSING LINE 415

# MISSING LINE 416

# MISSING LINE 417

# MISSING LINE 418

# MISSING LINE 419

# MISSING LINE 420

# MISSING LINE 421

# MISSING LINE 422

# MISSING LINE 423

# MISSING LINE 424

# MISSING LINE 425

# MISSING LINE 426

# MISSING LINE 427

# MISSING LINE 428

# MISSING LINE 429

# MISSING LINE 430

# MISSING LINE 431

# MISSING LINE 432

# MISSING LINE 433

# MISSING LINE 434

# MISSING LINE 435

# MISSING LINE 436

# MISSING LINE 437

# MISSING LINE 438

# MISSING LINE 439

# MISSING LINE 440

# MISSING LINE 441

# MISSING LINE 442

# MISSING LINE 443

# MISSING LINE 444

# MISSING LINE 445

# MISSING LINE 446

# MISSING LINE 447

# MISSING LINE 448

# MISSING LINE 449

# MISSING LINE 450

# MISSING LINE 451

# MISSING LINE 452

# MISSING LINE 453

# MISSING LINE 454

# MISSING LINE 455

# MISSING LINE 456

# MISSING LINE 457

# MISSING LINE 458

# MISSING LINE 459

# MISSING LINE 460

# MISSING LINE 461

# MISSING LINE 462

# MISSING LINE 463

# MISSING LINE 464

# MISSING LINE 465

# MISSING LINE 466

# MISSING LINE 467

# MISSING LINE 468

# MISSING LINE 469

# MISSING LINE 470

# MISSING LINE 471

# MISSING LINE 472

# MISSING LINE 473

# MISSING LINE 474

# MISSING LINE 475

# MISSING LINE 476

# MISSING LINE 477

# MISSING LINE 478

# MISSING LINE 479

# MISSING LINE 480

# MISSING LINE 481

# MISSING LINE 482

# MISSING LINE 483

# MISSING LINE 484

# MISSING LINE 485

# MISSING LINE 486

# MISSING LINE 487

# MISSING LINE 488

# MISSING LINE 489

# MISSING LINE 490

# MISSING LINE 491

# MISSING LINE 492

# MISSING LINE 493

# MISSING LINE 494

# MISSING LINE 495

# MISSING LINE 496

# MISSING LINE 497

# MISSING LINE 498

# MISSING LINE 499

# MISSING LINE 500

# MISSING LINE 501

# MISSING LINE 502

# MISSING LINE 503

# MISSING LINE 504

# MISSING LINE 505

# MISSING LINE 506

# MISSING LINE 507

# MISSING LINE 508

# MISSING LINE 509

# MISSING LINE 510

# MISSING LINE 511

# MISSING LINE 512

# MISSING LINE 513

# MISSING LINE 514

# MISSING LINE 515

# MISSING LINE 516

# MISSING LINE 517

# MISSING LINE 518

# MISSING LINE 519

# MISSING LINE 520

# MISSING LINE 521

# MISSING LINE 522

# MISSING LINE 523

# MISSING LINE 524

# MISSING LINE 525

# MISSING LINE 526

# MISSING LINE 527

# MISSING LINE 528

# MISSING LINE 529

# MISSING LINE 530

# MISSING LINE 531

# MISSING LINE 532

# MISSING LINE 533

# MISSING LINE 534

# MISSING LINE 535

# MISSING LINE 536

# MISSING LINE 537

# MISSING LINE 538

# MISSING LINE 539

# MISSING LINE 540

# MISSING LINE 541

# MISSING LINE 542

# MISSING LINE 543

# MISSING LINE 544

# MISSING LINE 545

# MISSING LINE 546

# MISSING LINE 547

# MISSING LINE 548

# MISSING LINE 549

# MISSING LINE 550

# MISSING LINE 551

# MISSING LINE 552

# MISSING LINE 553

# MISSING LINE 554

# MISSING LINE 555

# MISSING LINE 556

# MISSING LINE 557

# MISSING LINE 558

# MISSING LINE 559

# MISSING LINE 560

# MISSING LINE 561

# MISSING LINE 562

# MISSING LINE 563

# MISSING LINE 564

# MISSING LINE 565

# MISSING LINE 566

# MISSING LINE 567

# MISSING LINE 568

# MISSING LINE 569

# MISSING LINE 570

# MISSING LINE 571

# MISSING LINE 572

# MISSING LINE 573

# MISSING LINE 574

# MISSING LINE 575

# MISSING LINE 576

# MISSING LINE 577

# MISSING LINE 578

# MISSING LINE 579

# MISSING LINE 580

# MISSING LINE 581

# MISSING LINE 582

# MISSING LINE 583

# MISSING LINE 584

# MISSING LINE 585

# MISSING LINE 586

# MISSING LINE 587

# MISSING LINE 588

# MISSING LINE 589

# MISSING LINE 590

# MISSING LINE 591

# MISSING LINE 592

# MISSING LINE 593

# MISSING LINE 594

# MISSING LINE 595

# MISSING LINE 596

# MISSING LINE 597

# MISSING LINE 598

# MISSING LINE 599

# MISSING LINE 600

# MISSING LINE 601

# MISSING LINE 602

# MISSING LINE 603

# MISSING LINE 604

# MISSING LINE 605

# MISSING LINE 606

# MISSING LINE 607

# MISSING LINE 608

# MISSING LINE 609

# MISSING LINE 610

# MISSING LINE 611

# MISSING LINE 612

# MISSING LINE 613

# MISSING LINE 614

# MISSING LINE 615

# MISSING LINE 616

# MISSING LINE 617

# MISSING LINE 618

# MISSING LINE 619

# MISSING LINE 620

# MISSING LINE 621

# MISSING LINE 622

# MISSING LINE 623

# MISSING LINE 624

# MISSING LINE 625

# MISSING LINE 626

# MISSING LINE 627

# MISSING LINE 628

# MISSING LINE 629

# MISSING LINE 630

# MISSING LINE 631

# MISSING LINE 632

# MISSING LINE 633

# MISSING LINE 634

# MISSING LINE 635

# MISSING LINE 636

# MISSING LINE 637

# MISSING LINE 638

# MISSING LINE 639

# MISSING LINE 640

# MISSING LINE 641

# MISSING LINE 642

# MISSING LINE 643

# MISSING LINE 644

# MISSING LINE 645

# MISSING LINE 646

# MISSING LINE 647

# MISSING LINE 648

# MISSING LINE 649

# MISSING LINE 650

# MISSING LINE 651

# MISSING LINE 652

# MISSING LINE 653

# MISSING LINE 654

# MISSING LINE 655

# MISSING LINE 656

# MISSING LINE 657

# MISSING LINE 658

# MISSING LINE 659

# MISSING LINE 660

# MISSING LINE 661

# MISSING LINE 662

# MISSING LINE 663

# MISSING LINE 664

# MISSING LINE 665

# MISSING LINE 666

# MISSING LINE 667

# MISSING LINE 668

# MISSING LINE 669

# MISSING LINE 670

# ─────────────────────────────────────────────────────────────────────────────
# MODULAR PIPELINE STREAM
# ─────────────────────────────────────────────────────────────────────────────
async def _modular_pipeline_generator(
    creation_id: int,
    generate_ai_stencil: bool,
    vectorize: bool,
    convert_cad: bool,
    format_pdf: bool,
# MODULAR PIPELINE STREAM
# ─────────────────────────────────────────────────────────────────────────────
async def _modular_pipeline_generator(
    creation_id: int,
    generate_ai_stencil: bool,
    vectorize: bool,
    convert_cad: bool,
    format_pdf: bool,
    upscale: bool,
    generate_real_mockup: bool,
    use_ai_mockup: bool,
    package: bool,
    generate_seo: bool,
    theme: str,
    image_ai_provider: Optional[str] = "openai",
    text_ai_provider: Optional[str] = "gemini",
    design_style: Optional[str] = "classic",
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
    source_type: Optional[str] = None,
    output_assembled: bool = True,
    output_split: bool = False,
    strict_fidelity: bool = True,
    mockup_styles: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Streams progress for a modular pipeline on an already-created row."""
    db = SessionLocal()
    db_theme = None
    existing_source_png_path = None
    bundle_size = 4
    db_source_type = "text_prompt"
    try:
        settings = get_or_create_settings(db)
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            yield _sse("error", {"msg": f"Creation {creation_id} not found."})
            return
        db_theme = creation.theme
        existing_source_png_path = creation.source_png_path
        bundle_size = creation.bundle_size or 4
        db_source_type = creation.source_type or "text_prompt"
        settings_snap = {
            "gemini_key":   settings.gemini_key,
            "mistral_key":  settings.mistral_key,
            "openai_key":   settings.openai_key,
            "banana_key":   settings.banana_key,
            "replicate_key": settings.replicate_key,
            "openrouter_key": settings.openrouter_key,
            "huggingface_key": settings.huggingface_key,
            "anthropic_key": settings.anthropic_key,
            "stability_key": getattr(settings, "stability_key", None),
        db.close()
# MISSING LINE 732

    import re
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', theme or db_theme or "").strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation_id}"
# MISSING LINE 737

    resolved_source_type = (source_type or db_source_type or "text_prompt").lower().strip()
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
    source_filename = os.path.basename(existing_source_png_path) if existing_source_png_path else f"{safe_theme}_source.png"
# MISSING LINE 741

    source_png  = os.path.join(creation_dir, source_filename)
    svg_path    = os.path.join(creation_dir, f"{safe_theme}.svg")
    dxf_path    = os.path.join(creation_dir, f"{safe_theme}.dxf")
    ai_path     = os.path.join(creation_dir, f"{safe_theme}.ai")
# MISSING LINE 746

# MISSING LINE 747

# MISSING LINE 748

# MISSING LINE 749

# MISSING LINE 750

# MISSING LINE 751

# MISSING LINE 752

# MISSING LINE 753

# MISSING LINE 754

# MISSING LINE 755

# MISSING LINE 756

# MISSING LINE 757

# MISSING LINE 758

# MISSING LINE 759

# MISSING LINE 760

# MISSING LINE 761

# MISSING LINE 762

# MISSING LINE 763

# MISSING LINE 764

# MISSING LINE 765

# MISSING LINE 766

# MISSING LINE 767

# MISSING LINE 768

# MISSING LINE 769

# MISSING LINE 770

# MISSING LINE 771

# MISSING LINE 772

# MISSING LINE 773

# MISSING LINE 774

# MISSING LINE 775

# MISSING LINE 776

# MISSING LINE 777

# MISSING LINE 778

# MISSING LINE 779

# MISSING LINE 780

# MISSING LINE 781

# MISSING LINE 782

# MISSING LINE 783

# MISSING LINE 784

# MISSING LINE 785

# MISSING LINE 786

# MISSING LINE 787

# MISSING LINE 788

# MISSING LINE 789

# MISSING LINE 790

# MISSING LINE 791

# MISSING LINE 792

# MISSING LINE 793

# MISSING LINE 794

# MISSING LINE 795

# MISSING LINE 796

# MISSING LINE 797

# MISSING LINE 798

# MISSING LINE 799

# MISSING LINE 800

# MISSING LINE 801

# MISSING LINE 802

# MISSING LINE 803

# MISSING LINE 804

# MISSING LINE 805

# MISSING LINE 806

# MISSING LINE 807

# MISSING LINE 808

# MISSING LINE 809

# MISSING LINE 810

# MISSING LINE 811

# MISSING LINE 812

# MISSING LINE 813

# MISSING LINE 814

# MISSING LINE 815

# MISSING LINE 816

# MISSING LINE 817

# MISSING LINE 818

# MISSING LINE 819

# MISSING LINE 820

            _update_creation(
                creation_id,
                svg_path=f"/static/creation_{creation_id}/{os.path.basename(svg_path)}" if os.path.exists(svg_path) else None,
                source_png_path=f"/static/creation_{creation_id}/{os.path.basename(source_png)}" if os.path.exists(source_png) else None,
                upscale_png_path=f"/static/creation_{creation_id}/{os.path.basename(upscale_png)}" if os.path.exists(upscale_png) else None
            )
            yield _sse("image_ready", {
                "source_png_path": f"/static/creation_{creation_id}/{os.path.basename(source_png)}" if os.path.exists(source_png) else None
            })
            yield _sse("assets_ready", {
                "upscale_png_path": f"/static/creation_{creation_id}/{os.path.basename(upscale_png)}" if os.path.exists(upscale_png) else None
            })
# MISSING LINE 833

        elif resolved_source_type == "raw_image":
        elif resolved_source_type == "raw_image":
            if generate_ai_stencil:
                step += 1
                yield _status(step, "Génération IA du pochoir N&B (via Image source)...")
                _update_creation(creation_id, current_step="Génération Pochoir...")
                init_image = source_png + ".init.png"
                init_image = source_png + ".init.png"
                if os.path.exists(source_png):
                    shutil.copy(source_png, init_image)
                else:
                    init_image = None
                try:
                try:
                    stencil_result = await asyncio.to_thread(
                        generate_stencil_image,
                        settings_snap["image_ai_provider"],
                        settings_snap["banana_key"],
                        settings_snap["openai_key"],
                        theme or "Design",
                        source_png,
                        init_image_path=init_image,
                        bundle_size=bundle_size,
                        design_style=design_style,
                        gemini_key=settings_snap.get("gemini_key"),
                        replicate_key=settings_snap.get("replicate_key"),
                        openrouter_key=settings_snap.get("openrouter_key"),
                        huggingface_key=settings_snap.get("huggingface_key"),
                        stability_key=settings_s
                        vectorize=vectorize
                    )
                    )
                    # Binarization bypassed for AI stencil output
                    # Binarization bypassed for AI stencil output
                    pass
                    _update_creation(
                    _update_creation(
                        creation_id,
                        source_png_path=f"/static/creation_{creation_id}/{os.path.basename(source_png)}"
                    )
                    stencil_mod_provider = stencil_result.get("provider", settings_snap["image_ai_provider"]) if isinstance(stencil_result, dict) else settings_snap["image_ai_provider"]
                    stencil_mod_prompt = stencil_result.get("prompt", "") if isinstance(stencil_result, dict) else ""
                    stencil_status = "success"
                    stencil_status = "success"
                    stencil_error = None
                    if isinstance(stencil_result, dict) and stencil_result.get("status") == "degraded":
                        stencil_status = "degraded"
                        stencil_error = stencil_result.get("error")
                    yield f"data: {json.dumps({'component': 'stencil', 'status': 'success'})}\n\n"
                    yield f"data: {json.dumps({'component': 'stencil', 'status': 'success'})}\n\n"
                    yield _sse("image_ready", {
                        "source_png_path": f"/static/creation_{creation_id}/{os.path.basename(source_png)}",
                        "provider": stencil_mod_provider,
                        "prompt": stencil_mod_prompt,
                        "status": stencil_status,
                        "error": stencil_error
                    })
                except Exception as e:
                    print(f"CRITICAL STENCIL ERROR CAUGHT: {e}")
                    _update_creation(
                        creation_id,
                        status="failed",
                        failed_reason=f"Stencil generation failed: {e}",
                        current_step="Échec"
                    )
                    yield f"data: {json.dumps({'component': 'stencil', 'status': 'failed', 'error': str(e)})}\n\n"
                    return
# MISSING LINE 901

        elif resolved_source_type == "ready_bw_image":
            step += 1
            yield _status(step, "Binarisation et détourage de l'image...")
            _update_creation(creation_id, current_step="Détourage image...")
            try:
                await asyncio.to_thread(local_binarize_opaque, source_png, source_png)
                _update_creation(
                    creation_id,
                    source_png_path=f"/static/creation_{creation_id}/{os.path.basename(source_png)}"
                )
                yield _sse("image_ready", {
                    "source_png_path": f"/static/creation_{creation_id}/{os.path.basename(source_png)}"
                })
            except Exception as e:
                print(f"[pipeline] Binarization error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"Binarization failed: {e}", current_step="Échec")
                yield _sse("error", {"msg": f"La binarisation a échoué: {e}", "creation_id": creation_id})
                return
        elif resolved_source_type == "transparent_png":
        elif resolved_source_type == "transparent_p
# MISSING LINE 922

        elif resolved_source_type == "text_prompt":
            if generate_ai_stencil:
                step += 1
                yield _status(step, "Génération IA du pochoir N&B...")
                _update_creation(creation_id, current_step="Génération Pochoir...")
# MISSING LINE 928

                init_image = source_png + ".init.png"
                if os.path.exists(source_png):
                    shutil.copy(source_png, init_image)
                else:
                    init_image = None
# MISSING LINE 934

                try:
                    stencil_result = await asyncio.to_thread(
                        generate_stencil_image,
                        settings_snap["image_ai_provider"],
                        settings_snap["banana_key"],
                        settings_snap["openai_key"],
                        theme or "Design",
                        theme or "Design",
                        source_png,
                        init_image_path=init_image,
                        bundle_size=bundle_size,
                        design_style=design_style,
                        gemini_key=settings_snap.get("gemini_key"),
                        replicate_key=settings_snap.get("replicate_key"),
                        openrouter_key=settings_snap.get("openrouter_key"),
                        huggingface_key=settings_snap.get("huggingface_key"),
                        stability_key=settings_snap.get("stability_key"),
                        strict_fidelity=strict_fidelity,
                        vectorize=False
                    )
# MISSING LINE 955

                    # Binarization bypassed for AI stencil output
                    pass
# MISSING LINE 958

                    stencil_mod_provider = stencil_result.get("provider", settings_snap["image_ai_provider"]) if isinstance(stencil_result, dict) else settings_snap["image_ai_provider"]
                    stencil_mod_prompt = stencil_result.get("prompt", "") if isinstance(stencil_result, dict) else ""
                    vision_description = stencil_result.get("vision_description", "") if isinstance(stencil_result, dict) else ""
# MISSING LINE 962

                    stencil_status = "success"
                    stencil_error = None
                    if isinstance(stencil_result, dict) and stencil_result.get("status") == "degraded":
                        stencil_status = "degraded"
                        stencil_error = stencil_result.get("error")
# MISSING LINE 968

                    db_temp = SessionLocal()
                    existing_status = None
                    try:
                        cr_row = db_temp.query(Creation).filter(Creation.id == creation_id).first()
                        if cr_row and cr_row.pipeline_status:
                            try:
                                existing_status = json.loads(cr_row.pipeline_status)
                            except Exception:
                                pass
                    finally:
                        db_temp.close()
# MISSING LINE 980

                    if not existing_status:
                        existing_status = {
                            "stencil": {"status": "success", "paths": [], "error": None},
                            "seo": {"status": "success", "data": None, "error": None},
                            "mockup": {"status": "success", "paths": [], "error": None}
                        }
# MISSING LINE 987

                    existing_status["stencil"]["status"] = stencil_status
                    existing_status["stencil"]["error"] = stencil_error
                    existing_status["stencil"]["prompt"] = stencil_mod_prompt
                    existing_status["stencil"]["vision_description"] = vision_description
                    existing_status["stencil"]["paths"] = [f"/static/creation_{creation_id}/{os.path.basename(source_png)}"]
# MISSING LINE 993

                    _update_creation(
                        creation_id,
                        source_png_path=f"/static/creation_{creation_id}/{os.path.basename(source_png)}",
                        pipeline_status=json.dumps(existing_status)
                    )
# MISSING LINE 999

                    yield f"data: {json.dumps({'component': 'stencil', 'status': 'success'})}\n\n"
                    yield _sse("image_ready", {
                        "source_png_path": f"/static/creation_{creation_id}/{os.path.basename(source_png)}",
                        "provider": stencil_mod_provider,
                        "prompt": stencil_mod_prompt,
                        "vision_description": vision_description,
                        "status": stencil_status,
                        "error": stencil_error
                    })
                except Exception as e:
                    print(f"CRITICAL STENCIL ERROR CAUGHT: {e}")
# MISSING LINE 1011

# MISSING LINE 1012

# MISSING LINE 1013

# MISSING LINE 1014

# MISSING LINE 1015

# MISSING LINE 1016

# MISSING LINE 1017

# MISSING LINE 1018

# MISSING LINE 1019

# MISSING LINE 1020

# MISSING LINE 1021

# MISSING LINE 1022

# MISSING LINE 1023

# MISSING LINE 1024

# MISSING LINE 1025

# MISSING LINE 1026

# MISSING LINE 1027

# MISSING LINE 1028

# MISSING LINE 1029

# MISSING LINE 1030

# MISSING LINE 1031

# MISSING LINE 1032

# MISSING LINE 1033

# MISSING LINE 1034

# MISSING LINE 1035

# MISSING LINE 1036

# MISSING LINE 1037

# MISSING LINE 1038

# MISSING LINE 1039

# MISSING LINE 1040

# MISSING LINE 1041

# MISSING LINE 1042

# MISSING LINE 1043

# MISSING LINE 1044

# MISSING LINE 1045

# MISSING LINE 1046

# MISSING LINE 1047

# MISSING LINE 1048

# MISSING LINE 1049

# MISSING LINE 1050

# MISSING LINE 1051

# MISSING LINE 1052

# MISSING LINE 1053

# MISSING LINE 1054

# MISSING LINE 1055

# MISSING LINE 1056

# MISSING LINE 1057

# MISSING LINE 1058

# MISSING LINE 1059

# MISSING LINE 1060

# MISSING LINE 1061

# MISSING LINE 1062

# MISSING LINE 1063

# MISSING LINE 1064

# MISSING LINE 1065

# MISSING LINE 1066

# MISSING LINE 1067

# MISSING LINE 1068

# MISSING LINE 1069

# MISSING LINE 1070

# MISSING LINE 1071

# MISSING LINE 1072

# MISSING LINE 1073

# MISSING LINE 1074

# MISSING LINE 1075

# MISSING LINE 1076

# MISSING LINE 1077

# MISSING LINE 1078

# MISSING LINE 1079

# MISSING LINE 1080

# MISSING LINE 1081

# MISSING LINE 1082

# MISSING LINE 1083

# MISSING LINE 1084

# MISSING LINE 1085

# MISSING LINE 1086

# MISSING LINE 1087

# MISSING LINE 1088

# MISSING LINE 1089

# MISSING LINE 1090

# MISSING LINE 1091

# MISSING LINE 1092

# MISSING LINE 1093

# MISSING LINE 1094

# MISSING LINE 1095

# MISSING LINE 1096

# MISSING LINE 1097

# MISSING LINE 1098

# MISSING LINE 1099

# MISSING LINE 1100

# MISSING LINE 1101

# MISSING LINE 1102

# MISSING LINE 1103

# MISSING LINE 1104

# MISSING LINE 1105

# MISSING LINE 1106

# MISSING LINE 1107

# MISSING LINE 1108

# MISSING LINE 1109

# MISSING LINE 1110

# MISSING LINE 1111

# MISSING LINE 1112

# MISSING LINE 1113

# MISSING LINE 1114

# MISSING LINE 1115

# MISSING LINE 1116

# MISSING LINE 1117

# MISSING LINE 1118

# MISSING LINE 1119

# MISSING LINE 1120

# MISSING LINE 1121

# MISSING LINE 1122

# MISSING LINE 1123

# MISSING LINE 1124

# MISSING LINE 1125

# MISSING LINE 1126

# MISSING LINE 1127

# MISSING LINE 1128

# MISSING LINE 1129

# MISSING LINE 1130

# MISSING LINE 1131

# MISSING LINE 1132

# MISSING LINE 1133

# MISSING LINE 1134

# MISSING LINE 1135

# MISSING LINE 1136

# MISSING LINE 1137

# MISSING LINE 1138

# MISSING LINE 1139

# MISSING LINE 1140

# MISSING LINE 1141

# MISSING LINE 1142

# MISSING LINE 1143

# MISSING LINE 1144

# MISSING LINE 1145

# MISSING LINE 1146

# MISSING LINE 1147

# MISSING LINE 1148

# MISSING LINE 1149

# MISSING LINE 1150

# MISSING LINE 1151

# MISSING LINE 1152

# MISSING LINE 1153

# MISSING LINE 1154

# MISSING LINE 1155

# MISSING LINE 1156

# MISSING LINE 1157

# MISSING LINE 1158

# MISSING LINE 1159

# MISSING LINE 1160

# MISSING LINE 1161

# MISSING LINE 1162

# MISSING LINE 1163

# MISSING LINE 1164

# MISSING LINE 1165

# MISSING LINE 1166

# MISSING LINE 1167

# MISSING LINE 1168

# MISSING LINE 1169

# MISSING LINE 1170

# MISSING LINE 1171

# MISSING LINE 1172

# MISSING LINE 1173

# MISSING LINE 1174

# MISSING LINE 1175

# MISSING LINE 1176

# MISSING LINE 1177

# MISSING LINE 1178

# MISSING LINE 1179

# MISSING LINE 1180

# MISSING LINE 1181

# MISSING LINE 1182

# MISSING LINE 1183

# MISSING LINE 1184

# MISSING LINE 1185

# MISSING LINE 1186

# MISSING LINE 1187

# MISSING LINE 1188

# MISSING LINE 1189

# MISSING LINE 1190

# MISSING LINE 1191

# MISSING LINE 1192

# MISSING LINE 1193

# MISSING LINE 1194

# MISSING LINE 1195

# MISSING LINE 1196

# MISSING LINE 1197

# MISSING LINE 1198

# MISSING LINE 1199

        if format_pdf:
            step += 1
            yield _status(step, f"Génération PDF ({len(elements)} éléments)...")
            pdf_urls = []
            try:
                for el in elements:
                    png_src = el["upscale_png"] if os.path.exists(el["upscale_png"]) else el["source_png"]
                    await asyncio.to_thread(png_to_pdf, png_src, el["pdf_path"])
                    if os.path.exists(el["pdf_path"]):
                        pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")
            except Exception as e:
                print(f"[pipeline] PDF generation error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"PDF generation failed: {e}", current_step="Échec")
                yield _sse("error", {"msg": f"La génération PDF a échoué: {e}", "creation_id": creation_id})
                return
# MISSING LINE 1215

            _update_creation(
                creation_id,
                pdf_path=pdf_urls[0] if pdf_urls else None,
                pdf_paths=pdf_urls,
            )
            yield _sse("assets_ready", {
                "pdf_path": pdf_urls[0] if pdf_urls else None,
                "pdf_paths": pdf_urls,
            })
# MISSING LINE 1225

        # ── RESOLVE AI BACKDROP FOR MOCKUPS ──
        bg_temp_file = None
        if generate_real_mockup:
            if use_ai_mockup:
                    if os.path.exists(el["pdf_path"]):
                        pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")
            except Exception as e:
                print(f"[pipeline] PDF generation error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"PDF generation failed: {e}", current_step="Échec")
                yield _sse("error", {"msg": f"La génération PDF a échoué: {e}", "creation_id": creation_id})
                return
                    )
            _update_creation(
                creation_id,
                pdf_path=pdf_urls[0] if pdf_urls else None,
                pdf_paths=pdf_urls,
            )
            yield _sse("assets_ready", {
                "pdf_path": pdf_urls[0] if pdf_urls else None,
                "pdf_paths": pdf_urls,
            })
        try:
        # ── RESOLVE AI BACKDROP FOR MOCKUPS ──
        bg_temp_file = None
            )
            yield _sse("assets_ready", {
                "pdf_path": pdf_urls[0] if pdf_urls else None,
                "pdf_paths": pdf_urls,
            })
                    backdrop_bytes = await asyncio.to_thread(
        # ── RESOLVE AI BACKDROP FOR MOCKUPS ──
        bg_temp_file = None
        if generate_real_mockup:
            if use_ai_mockup:
                try:
                    from ..services.image_engine import generate_mockup_backdrop
                    print(f"[pipeline] Generating AI room backdrop for theme: {theme or 'Design'}")
                    backdrop_bytes = await asyncio.to_thread(
                        generate_mockup_backdrop,
                        theme or "Design",
                        settings_snap["openai_key"]
                    )
                    import tempfile
                    temp_bg = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    temp_bg.write(backdrop_bytes)
                    temp_bg.close()
                    bg_temp_file = temp_bg.name
                    print(f"[pipeline] AI room backdrop generated and saved to: {bg_temp_file}")
                except Exception as bg_err:
                    print(f"[pipeline] AI backdrop generation failed: {bg_err}. Falling back to default backgrounds.")
                        True
        try:
            # ── PREMIUM 3D METAL MOCKUP (generate_real_mockup) ──
            if gen
                        creation_id,
                        mockup_path=f"/static/creation_{creation_id}/{os.path.basename(mockup_raw)}",
                        real_mockup_path=f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial)}"
                    )
# MISSING LINE 1284

                    yield _sse("mockup_ready", {"mockup_path": f"/static/creation_{creation_id}/{os.path.basename(mockup_raw)}"})
                    yield _sse("real_mockup_ready", {"real_mockup_path": f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial)}"})
                    yield f"data: {json.dumps({'component': 'mockup_raw', 'status': 'success'})}\n\n"
                    yield f"data: {json.dumps({'component': 'mockup_commercial', 'status': 'success'})}\n\n"
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await asyncio.to_thread(
                        composite_stencil_on_bg,
                        png_for_real_mockup,
                        bg_temp_file,
                        mockup_commercial,
                        "matte_black_metal",
                        True
                    )
# MISSING LINE 1300

                    _update_creation(
                        creation_id,
                        mockup_path=f"/static/creation_{creation_id}/{os.path.basename(mockup_raw)}",
                        real_mockup_path=f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial)}"
                    )
            for el in elements:
                    )
                    yield _sse("real_mockup_ready", {"real_mockup_path": f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial)}"})
                    _update_creation(
                        creation_id,
                        mockup_path=f"/static/creation_{creation_id}/{os.path.basename(mockup_raw)}",
                        real_mockup_path=f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial)}"
                    )
                    yield f"data: {json.dumps({'component': 'real_mockup', 'status': 'failed', 'error': str(e)})}\n\n"
                    yield _sse("mockup_ready", {"mockup_path": f"/static/creation_{creation_id}/{os.path.basename(mockup_raw)}"})
                    yield _sse("real_mockup_ready", {"real_mockup_path": f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial)}"})
                    yield f"data: {json.dumps({'component': 'mockup_raw', 'status': 'success'})}\n\n"
                    yield f"data: {json.dumps({'component': 'mockup_commercial', 'status': 'success'})}\n\n"
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    yield f"data: {json.dumps({'component': 'real_mockup', 'status': 'failed', 'error': str(e)})}\n\n"
        finally:
            if bg_temp_file and os.path.exists(bg_temp_file):
                try:
                    os.remove(bg_temp_file)
                    print(f"[pipeline] Cleaned up temporary AI backdrop file: {bg_temp_file}")
                except Exception as cleanup_err:
                    print(f"[pipeline] Failed to clean up temporary background file: {cleanup_err}")
# MISSING LINE 1330

        # ── PACKAGE ZIP (Includes all elements) ──
        if package:
            step += 1
            yield _status(step, "Création du package client ZIP...")
            assets = []
            for el in elements:
                for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                    p = el[path_key]
                    if p and os.path.exists(p):
                        assets.append(p)
# MISSING LINE 1341

            # Zip includes both fresh mockup paths
            for m_file in [
                os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg"),
                os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
            ]:
                if os.path.exists(m_file):
                    assets.append(m_file)
# MISSING LINE 1349

            assets = list(dict.fromkeys(assets))
            try:
                await asyncio.to_thread(package_assets, assets, zip_path)
                _update_creation(creation_id, zip_path=f"/static/creation_{creation_id}/{os.path.basename(zip_path)}")
                yield _sse("assets_ready", {"zip_path": f"/static/creation_{creation_id}/{os.path.basename(zip_path)}"})
            except Exception as e:
                print(f"[pipeline] ZIP packaging error: {e}")
                _update_creation(creation_id, status="failed", failed_reason=f"ZIP packaging failed: {e}", current_step="Échec")
                yield _sse("error", {"msg": f"La création du ZIP a échoué: {e}", "creation_id": creation_id})
                return
# MISSING LINE 1360

        # ── SEO AND COPYWRITING ──
        if generate_seo and theme:
            step += 1
            yield _status(step, f"Rédaction SEO bilingue ({settings_snap['text_ai_provider']})...")
            try:
# MISSING LINE 1366

# MISSING LINE 1367

# MISSING LINE 1368

# MISSING LINE 1369

# MISSING LINE 1370

# MISSING LINE 1371

# MISSING LINE 1372

# MISSING LINE 1373

# MISSING LINE 1374

# MISSING LINE 1375

# MISSING LINE 1376

# MISSING LINE 1377

# MISSING LINE 1378

# MISSING LINE 1379

# MISSING LINE 1380

# MISSING LINE 1381

# MISSING LINE 1382

# MISSING LINE 1383

# MISSING LINE 1384

# MISSING LINE 1385

# MISSING LINE 1386

# MISSING LINE 1387

# MISSING LINE 1388

# MISSING LINE 1389

# MISSING LINE 1390

# MISSING LINE 1391

# MISSING LINE 1392

# MISSING LINE 1393

# MISSING LINE 1394

# MISSING LINE 1395

# MISSING LINE 1396

# MISSING LINE 1397

# MISSING LINE 1398

# MISSING LINE 1399

# MISSING LINE 1400

# MISSING LINE 1401

# MISSING LINE 1402

# MISSING LINE 1403

# MISSING LINE 1404

# MISSING LINE 1405

# MISSING LINE 1406

# MISSING LINE 1407

# MISSING LINE 1408

# MISSING LINE 1409

            theme,
            session_token,
            creation_id,
            design_style=design_style,
            bundle_size=bundle_size,
            preferred_image_provider=pref_img,
            preferred_text_provider=pref_txt,
            profile_tier=profile_tier
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
# MISSING LINE 1426

# MISSING LINE 1427

@router.get("/stream/modular")
async def stream_modular_pipeline(
    creation_id: int,
    theme: str = "",
    generate_ai_stencil: bool = False,
    vectorize: bool = False,
    convert_cad: bool = False,
    format_pdf: bool = False,
    upscale: bool = False,
    generate_real_mockup: bool = False,
    use_ai_mockup: bool = False,
    package: bool = False,
    generate_seo: bool = False,
    image_ai_provider: Optional[str] = None,
    text_ai_provider: Optional[str] = None,
    design_style: Optional[str] = "classic",
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
    source_type: Optional[str] = None,
    output_assembled: bool = True,
    output_split: bool = False,
    strict_fidelity: bool = True
):
    pref_img = preferred_image_provider or image_ai_provider
    pref_txt = preferred_text_provider or text_ai_provider
    return StreamingResponse(
        _modular_pipeline_generator(
            creation_id=creation_id,
            generate_ai_stencil=generate_ai_stencil,
            vectorize=vectorize,
            convert_cad=convert_cad,
@router.get("/stream/modular")
async def stream_modular_pipeline(
    creation_id: int,
    theme: str = "",
    generate_ai_stencil: bool = False,
    vectorize: bool = False,
    convert_cad: bool = False,
    format_pdf: bool = False,
    upscale: bool = False,
    generate_real_mockup: bool = False,
    use_ai_mockup: bool = False,
    package: bool = False,
    generate_seo: bool = False,
    image_ai_provider: Optional[str] = None,
    text_ai_provider: Optional[str] = None,
    design_style: Optional[str] = "classic",
    preferred_image_provider: Optional[str] = None,
    preferred_text_provider: Optional[str] = None,
    source_type: Optional[str] = None,
    output_assembled: bool = True,
    output_split: bool = False,
    strict_fidelity: bool = True,
    mockup_styles: Optional[str] = None
):
    pref_img = preferred_image_provider or image_ai_provider
    pref_txt = preferred_text_provider or text_ai_provider
    return StreamingResponse(
        _modular_pipeline_generator(
            creation_id=creation_id,
            generate_ai_stencil=generate_ai_stencil,
            vectorize=vectorize,
            convert_cad=convert_cad,
            format_pdf=format_pdf,
            upscale=upscale,
            generate_real_mockup=generate_real_mockup,
            use_ai_mockup=use_ai_mockup,
            package=package,
            generate_seo=generate_seo,
            theme=theme,
            image_ai_provider=pref_img,
            text_ai_provider=pref_txt,
            design_style=design_style,
            source_type=source_type,
            output_assembled=output_assembled,
            output_split=output_split,
            strict_fidelity=strict_fidelity,
            mockup_styles=mockup_styles
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
@router.get("/stream/image")
async def stream_image(
    prompt: str,
    init_image_path: Optional[str] = None,
    db: Session = Depends(get_db)
):
    settings = get_or_create_settings(db)
    openai_key = settings.openai_key or os.getenv("OPENAI_API_KEY") or ""
    if not openai_key:
        raise HTTPException(status_code=400, detail="OpenAI API Key is missing.")
    return StreamingResponse(
        stream_dalle_image_progressive(openai_key, prompt, init_image_path),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
# MISSING LINE 1535

    # Determine first file
# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD FILE FOR MODULAR MODE
# ─────────────────────────────────────────────────────────────────────────────
from fastapi import UploadFile, File, Form
from ..schemas import CreationResponse
            inferred_type = "vector_svg"
# MISSING LINE 1543

@router.post("/upload", response_model=CreationResponse)
async def upload_source_file(
    files: Optional[list[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    theme: str = Form("Fichier Importé"),
    bundle_size: int = Form(1),
    design_style: str = Form("classic"),
    source_type: Optional[str] = Form(None),
    source_is_multi_element: str = Form("single"),
    output_assembled: bool = Form(True),
    output_split: bool = Form(False),
    strict_fidelity: bool = Form(True),
    db: Session = Depends(get_db),
):
    # Resolve files
    uploaded_files = []
    if files:
        uploaded_files = files
    elif file:
        uploaded_files = [file]
    saved_paths = []
    if not uploaded_files and not image_url and source_type != "text_prompt":
        raise HTTPException(status_code=400, detail="Aucun fichier ou image_url fourni.")
    def _save_upload_sync(file_file, path):
    # Intercept mask upload to strictly save it in tempfile directory to prevent DB pollution
    if theme.startswith("mask_") or theme.startswith("mask"):
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
            inferred_type = "vector_svg"
        # Save uploaded file
        if uploaded_files:
            with open(temp_file_path, "wb") as f_out:
                shutil.copyfileobj(uploaded_files[0].file, f_out)
        elif image_url:
            resp = requests.get(image_url, timeout=15)
            resp.raise_for_status()
            with open(temp_file_path, "wb") as f_out:
                f_out.write(resp.content)
    db.add(creation)
        return {
            "id": 0,
            "theme": theme,
            "source_png_path": temp_file_path,
            "status": "pending",
            "timestamp": datetime.utcnow(),
            "is_published_etsy": False,
            "bundle_size": 1,
            "source_type": "ready_bw_image"
        }
        else:
    # Determine first file
    ref_filename = uploaded_files[0].filename if uploaded_files else (image_url or "file.png")
    inferred_type = source_type
    if not inferred_type:
        inferred_type = "raw_image"
        if ref_filename.lower().endswith(".svg"):
            inferred_type = "vector_svg"
    elif is_svg:
    creation = Creation(
        theme=theme,
        timestamp=datetime.utcnow(),
        is_published_etsy=False,
        status="pending",
        bundle_size=bundle_size if len(uploaded_files) <= 1 else len(uploaded_files),
        source_type=inferred_type,
    )
    db.add(creation)
    db.commit()
    db.refresh(creation)
            saved_paths.append(target_path)
    creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation.id}")
    os.makedirs(creation_dir, exist_ok=True)
            await asyncio.to_thread(_save_upload_sync, f_obj.file, target_path)
    import re
    safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', theme).strip('_')
    if not safe_theme:
        safe_theme = f"design_{creation.id}"
        suffix = ""
    # For multiple files, save each file. First file is the reference master source.
    saved_paths = []
    is_svg = ref_filename.lower().endswith(".svg") or inferred_type == "vector_svg"
            saved_paths.append(target_path)
    def _save_upload_sync(file_file, path):
        with open(path, "wb") as f_out:
            shutil.copyfileobj(file_file, f_out)
            saved_paths.append(target_path)
    def _download_url_sync(url, path):
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        with open(path, "wb") as f_out:
            f_out.write(resp.content)
        creation.svg_path = f"/static/creation_{creation.id}/{os.path.basename(saved_paths[0])}"
    for idx, f_obj in enumerate(uploaded_files):
        suffix = f"_{idx+1}" if len(uploaded_files) > 1 else ""
        if is_svg:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.svg")
            await asyncio.to_thread(_save_upload_sync, f_obj.file, target_path)
            saved_paths.append(target_path)
        else:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.png")
            await asyncio.to_thread(_save_upload_sync, f_obj.file, target_path)
            saved_paths.append(target_path)
def reprocess_creation_assets(creation_id: int):
    # Handle image url fallback
    if not uploaded_files and image_url:
        suffix = ""
        if is_svg:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.svg")
            await asyncio.to_thread(_download_url_sync, image_url, target_path)
            saved_paths.append(target_path)
        else:
            target_path = os.path.join(creation_dir, f"{safe_theme}{suffix}_source.png")
            await asyncio.to_thread(_download_url_sync, image_url, target_path)
            saved_paths.append(target_path)
        # Setup paths
        creation_dir = os.path.join(STORAGE_DIR, f"creation_{creation_id}")
        import re
        safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
        if not safe_theme:
            safe_theme = f"design_{creation_id}"
        eps_urls = []
        source_png = os.path.join(creation_dir, f"{safe_theme}_source.png")
        binarized_png = os.path.join(creation_dir, f"{safe_theme}_binarized.png")
# MISSING LINE 1670

        # 1. Binarize
        local_binarize_image(source_png, binarized_png)
# MISSING LINE 1673

        # 2. Slice
        bundle_size = creation.bundle_size or 4
        element_paths = []
        if bundle_size > 1 and (creation.source_type or "text_prompt") != "vector_svg":
            element_paths = split_multielement_image(binarized_png, creation_dir, bundle_size)
        if not element_paths:
            element_paths = [binarized_png]
            svg_to_dxf(inkscape_bin, el["svg_path"], el["dxf_path"], png_source_path=el["source_png"])
        elements = []
        for idx, el_png in enumerate(element_paths):
            el_name = f"{safe_theme}_{idx+1}" if len(element_paths) > 1 else safe_theme
            elements.append({
                "source_png": el_png,
                "base_name": el_name,
                "svg_path": os.path.join(creation_dir, f"{el_name}.svg"),
                "dxf_path": os.path.join(creation_dir, f"{el_name}.dxf"),
                "ai_path": os.path.join(creation_dir, f"{el_name}.ai"),
                "eps_path": os.path.join(creation_dir, f"{el_name}.eps"),
                "pdf_path": os.path.join(creation_dir, f"{el_name}.pdf"),
                "upscale_png": os.path.join(creation_dir, f"{el_name}.png"),
            })
# MISSING LINE 1695

        # 3. Vectorize, CAD, Upscale, PDF
        svg_urls = []
        dxf_urls = []
        ai_urls = []
        eps_urls = []
                pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")
# MISSING LINE 1702

        # 4. Mockups
        master_upscale = os.path.join(creation_dir, f"{safe_theme}_master_upscaled.png")
        if os.path.exists(binarized_png):
            convert_to_transparent_png(binarized_png, master_upscale, 3)
        png_for_mockup = master_upscale if os.path.exists(master_upscale) else binarized_png
# MISSING LINE 1708

        mockup_raw_path = os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg")
        mockup_commercial_path = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
# MISSING LINE 1711

        try:
            from ..services.image_engine import generate_mockup_backdrop
            backdrop_bytes = generate_mockup_backdrop(creation.theme or "Design", settings.openai_key)
            import tempfile
            temp_bg = tempfile.mktemp(suffix=".jpg")
            with open(temp_bg, 'wb') as f:
                f.write(backdrop_bytes)
# MISSING LINE 1719

            from ..services.mockup_engine import composite_stencil_on_bg
# MISSING LINE 1721

            # Export 1: Raw Mockup
            composite_stencil_on_bg(
                stencil_path=png_for_mockup,
                bg_path=temp_bg,
                output_path=mockup_raw_path,
                material="matte_black_metal",
                apply_tp_overlay=False
            )
# MISSING LINE 1730

            # PDF
            png_to_pdf(el["upscale_png"] if os.path.exists(el["upscale_png"]) else el["source_png"], el["pdf_path"])
            if os.path.exists(el["pdf_path"]):
                pdf_urls.append(f"/static/creation_{creation_id}/{os.path.basename(el['pdf_path'])}")
                output_path=mockup_commercial_path,
        # 4. Mockups
        master_upscale = os.path.join(creation_dir, f"{safe_theme}_master_upscaled.png")
        if os.path.exists(binarized_png):
            convert_to_transparent_png(binarized_png, master_upscale, 3)
        png_for_mockup = master_upscale if os.path.exists(master_upscale) else binarized_png
                os.remove(temp_bg)
        mockup_raw_path = os.path.join(creation_dir, f"{safe_theme}_mockup_raw.jpg")
        mockup_commercial_path = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial.jpg")
# MISSING LINE 1744

        try:
            from ..services.image_engine import generate_mockup_backdrop
            backdrop_bytes = generate_mockup_backdrop(creation.theme or "Design", settings.openai_key)
            import tempfile
            temp_bg = tempfile.mktemp(suffix=".jpg")
            with open(temp_bg, 'wb') as f:
                f.write(backdrop_bytes)
                    assets_to_zip.append(p)
            from ..services.mockup_engine import composite_stencil_on_bg
            if os.path.exists(m_file):
            # Export 1: Raw Mockup
            composite_stencil_on_bg(
                stenc
            package_assets(assets_to_zip, zip_path)
# MISSING LINE 1759

        # Update DB
        creation.svg_path = svg_urls[0] if svg_urls else None
        creation.svg_paths = svg_urls
        creation.dxf_path = dxf_urls[0] if dxf_urls else None
        creation.ai_path = ai_urls[0] if ai_urls else None
        creation.eps_path = eps_urls[0] if eps_urls else None
        creation.upscale_png_path = png_urls[0] if png_urls else None
        creation.png_paths = png_urls
        creation.pdf_path = pdf_urls[0] if pdf_urls else None
        creation.pdf_paths = pdf_urls
        creation.mockup_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_raw_path)}" if os.path.exists(mockup_raw_path) else None
        creation.real_mockup_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial_path)}" if os.path.exists(mockup_commercial_path) else None
        creation.zip_path = f"/static/creation_{creation_id}/{os.path.basename(zip_path)}" if os.path.exists(zip_path) else None
        creation.status = "completed"
        creation.current_step = "Terminé ✓"
        db.commit()
    except Exception as e:
        print(f"[pipeline] Downstream regeneration error: {e}")
        import traceback
        traceback.print_exc()
                )
                # Commercial Mockup
                composite_stencil_on_bg(
                    stencil_path=png_for_mockup,
                    bg_path=temp_bg,
                    output_path=mockup_commercial_path,
                    material="matte_black_metal",
                    apply_tp_overlay=True
                )
        if assets_to_zip:
                if idx == 0:
                    first_raw_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_raw_path)}"
                    first_comm_path = f"/static/creation_{creation_id}/{os.path.basename(mockup_commercial_path)}"
        # Update DB
                if os.path.exists(temp_bg):
                    os.remove(temp_bg)
        except Exception as mockup_err:
            print(f"[pipeline] Reprocess Mockup dual-processing failed: {mockup_err}")
        creation.eps_path = eps_urls[0] if eps_urls else None
        # 5. ZIP
        zip_path = os.path.join(creation_dir, f"{safe_theme}.zip")
        assets_to_zip = []
        for el in elements:
            for path_key in ["svg_path", "dxf_path", "ai_path", "eps_path", "pdf_path", "upscale_png"]:
                p = el[path_key]
                if p and os.path.exists(p):
                    assets_to_zip.append(p)
        creation.current_step = "Terminé ✓"
        # Include all fresh mockup paths in ZIP
        for idx in range(len(parsed_styles)):
            raw_path = os.path.join(creation_dir, f"{safe_theme}_mockup_raw_{idx+1}.jpg")
            comm_path = os.path.join(creation_dir, f"{safe_theme}_mockup_commercial_{idx+1}.jpg")
            if os.path.exists(raw_path):
                assets_to_zip.append(raw_path)
            if os.path.exists(comm_path):
                assets_to_zip.append(comm_path)
        # e.g., /static/creation_1/design_1_source.png -> backend/storage/creation_1/design_1_source.png
        if assets_to_zip:
            assets_to_zip = list(dict.fromkeys(assets_to_zip))
            package_assets(assets_to_zip, zip_path)
# MISSING LINE 1820

        # Update DB
        creation.svg_path = svg_urls[0] if svg_urls else None
        creation.svg_paths = svg_urls
        creation.dxf_path = dxf_urls[0] if dxf_urls else None
        creation.ai_path = ai_urls[0] if ai_urls else None
        creation.eps_path = eps_urls[0] if eps_urls else None
        creation.upscale_png_path = png_urls[0] if png_urls else None
        creation.png_paths = png_urls
        creation.pdf_path = pdf_urls[0] if pdf_urls else None
        creation.pdf_paths = pdf_urls
        creation.mockup_path = first_raw_path
        creation.real_mockup_path = first_comm_path
        creation.zip_path = f"/static/creation_{creation_id}/{os.path.basename(zip_path)}" if os.path.exists(zip_path) else None
        creation.status = "completed"
        creation.current_step = "Terminé ✓"
        db.commit()
    except Exception as e:
        print(f"[pipeline] Downstream regeneration error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
# MISSING LINE 1843

        # Enforce automatic downstream regeneration
@router.post("/inpainting")
async def pipeline_inpainting(
    background_tasks: BackgroundTasks,
    image_path: str = Form(...),
    mask_path: str = Form(...),
    prompt: str = Form(...),
    output_path: str = Form(...),
    creation_id: int = Form(...)
):
    try:
        from ..services.image_engine import execute_inpainting
        from ..routers.settings import get_or_create_settings
        db = SessionLocal()
        settings = get_or_create_settings(db)
        openai_key = settings.openai_key
        db.close()
# MISSING LINE 1861

        # Strip local server domain prefix if accidentally appended by the frontend
        for var_name in ["image_path", "mask_path", "output_path"]:
            val = locals().get(var_name)
            if val and (val.startswith("http://") or val.startswith("https://")):
                import urllib.parse
                parsed_url = urllib.parse.urlparse(val)
                if "127.0.0.1" in parsed_url.netloc or "localhost" in parsed_url.netloc:
                    if var_name == "image_path":
                        image_path = parsed_url.path
                    elif var_name == "mask_path":
                        mask_path = parsed_url.path
                    elif var_name == "output_path":
                        output_path = parsed_url.path
# MISSING LINE 1875

        # Convert web relative paths to server local paths if necessary
        # e.g., /static/creation_1/design_1_source.png -> backend/storage/creation_1/design_1_source.png
        image_path_clean = image_path.split("?")[0]
        mask_path_clean = mask_path.split("?")[0]
        output_path_clean = output_path.split("?")[0]
# MISSING LINE 1881

        local_img = image_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_mask = mask_path_clean.replace("/static/", STORAGE_DIR + "/")
        local_out = output_path_clean.replace("/static/", STORAGE_DIR + "/")
# MISSING LINE 1885

        # Make directories if needed
        os.makedirs(os.path.dirname(local_out), exist_ok=True)
# MISSING LINE 1888

        await asyncio.to_thread(
            execute_inpainting,
            local_img,
            local_mask,
            prompt,
            local_out,
            openai_key
        )
# MISSING LINE 1897

        # Binarize output to ensure it remains a pure black/white stencil
        from ..services.image_engine import local_binarize_opaque
        await asyncio.to_thread(local_binarize_opaque, local_out, local_out)
# MISSING LINE 1901

        # Update creation paths if needed
        _update_creation(creation_id, source_png_path=output_path_clean)
# MISSING LINE 1904

        # Enforce automatic downstream regeneration
        background_tasks.add_task(reprocess_creation_assets, creation_id)
# MISSING LINE 1907

        return {"status": "success", "output_path": output_path_clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# MISSING LINE 1911

# MISSING LINE 1912

@router.post("/local-correction")
async def pipeline_local_correction(
    background_tasks: BackgroundTasks,
# MISSING LINE 1916

# MISSING LINE 1917

# MISSING LINE 1918

# MISSING LINE 1919

            local_mask,
            prompt,
            local_out,
            openai_key
        )
# MISSING LINE 1925

        # Binarize output to ensure it remains a pure black/white stencil
        from ..services.image_engine import local_binarize_opaque
        await asyncio.to_thread(local_binarize_opaque, local_out, local_out)
# MISSING LINE 1929

        # Update creation paths if needed
        _update_creation(creation_id, source_png_path=output_path_clean)
# MISSING LINE 1932

        # Enforce automatic downstream regeneration
        background_tasks.add_task(reprocess_creation_assets, creation_id)
# MISSING LINE 1935

        return {"status": "success", "output_path": output_path_clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# MISSING LINE 1939

# MISSING LINE 1940

@router.post("/local-correction")
async def pipeline_local_correction(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    creation_id: int = Form(...),
    output_path: str = Form(...)
):
    try:
        # Strip local server domain prefix if accidentally appended by the frontend
        if output_path.startswith("http://") or output_path.startswith("https://"):
# MISSING LINE 1951

# MISSING LINE 1952

# MISSING LINE 1953

# MISSING LINE 1954

# MISSING LINE 1955

# MISSING LINE 1956

# MISSING LINE 1957

# MISSING LINE 1958

# MISSING LINE 1959

# MISSING LINE 1960

# MISSING LINE 1961

# MISSING LINE 1962

# MISSING LINE 1963

# MISSING LINE 1964

# MISSING LINE 1965

# MISSING LINE 1966

# MISSING LINE 1967

# MISSING LINE 1968

# MISSING LINE 1969

    theme: Optional[str] = None
    canvas_data: Optional[str] = None  # Holds the serialized canvas strokes/mask data
    canvasData: Optional[str] = None  # Alias/Fallback for compatibility
    asset_path: Optional[str] = None
    asset_type: Optional[str] = "master_stencil"
            except Exception as mockup_err:
    class Config:
        from_attributes = True
            creation.mockup_path = f"/static/creation_{creation.id}/{os.path.basename(mockup_raw_path)}" if os.path.exists(mockup_raw_path) else None
            creation.real_mockup_path = f"/static/creation_{creation.id}/{os.path.basename(mockup_commercial_path)}" if os.path.exists(mockup_commercial_path) else None
def run_downstream_pipeline_operations(creation_id: int, local_path: str, asset_type: str):
    db = SessionLocal()
    try:
        creation = db.query(Creation).filter(Creation.id == creation_id).first()
        if not creation:
            return
        import traceback
        if asset_type == "master_stencil":
            from ..services.image_engine import local_binarize_opaque
            local_binarize_opaque(local_path, local_path)
            reprocess_creation_assets(creation.id)
# MISSING LINE 1991

        elif asset_type == "split_element":
            from ..services.image_engine import convert_to_transparent_png
            convert_to_transparent_png(local_path, local_path, 3)
    background_tasks: BackgroundTasks,
            settings = get_or_create_settings(db)
            creation_dir = os.path.dirname(local_path)
            import re
            safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
            if not safe_theme:
                safe_theme = f"design_{creation.id}"
# MISSING LINE 2002

            mockup_raw_path = os.path.join(crea
# MISSING LINE 2004

            if asset_path.startswith("http://") or asset_path.startswith("https://"):
                asset_path = "/" + asset_path.split("/", 3)[-1]
            local_path = asset_path.replace("/static/", STORAGE_DIR + "/")
        else:
            source_png_path = creation.source_png_path
            if not source_png_path:
                import re
                safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
                if not safe_theme:
                    safe_theme = f"design_{creation.id}"
                source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.png"
                # Export 1: Raw Mockup (WITHOUT watermark)
                composite_stencil_on_bg(
                    stencil_path=local_path,
                    bg_path=temp_bg,
                    output_path=mockup_raw_path,
                    material="matte_black_metal",
                    apply_tp_overlay=False
                )
            raise HTTPException(status_code=400, detail="Missing canvasData or canvas_data")
                # Export 2: Commercial Mockup (WITH watermark)
                composite_stencil_on_bg(
                    stencil_path=local_path,
                    bg_path=temp_bg,
                    output_path=mockup_commercial_path,
                    material="matte_black_metal",
                    apply_tp_overlay=True
                )
        asset_type = req.asset_type or "master_stencil"
                if os.path.exists(temp_bg):
                    os.remove(temp_bg)
            except Exception as mockup_err:
                print(f"[pipeline] split_element mockup generation failed: {mockup_err}")
        db.commit()
            creation.mockup_path = f"/static/creation_{creation.id}/{os.path.basename(mockup_raw_path)}" if os.path.exists(mockup_raw_path) else None
            creation.real_mockup_path = f"/static/creation_{creation.id}/{os.path.basename(mockup_commercial_path)}" if os.path.exists(mockup_commercial_path) else None
            creation.status = "completed"
            creation.current_step = "Terminé ✓"
            db.commit()
            local_path=local_path,
    except Exception as e:
        print(f"[pipeline] Background processing failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        }
    except Exception as e:
@router.post("/save-workspace", status_code=202)
async def save_workspace_canvas(
    req: SaveWorkspaceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        creation = db.query(Creation).filter(Creation.id == req.creation_id).first()
        if not creation:
            raise HTTPException(status_code=404, detail="Creation non trouvée")
# MISSING LINE 2063

        asset_path = req.asset_path
        if asset_path:
            if asset_path.startswith("http://") or asset_path.startswith("https://"):
                asset_path = "/" + asset_path.split("/", 3)[-1]
            local_path = asset_path.replace("/static/", STORAGE_DIR + "/")
        else:
            source_png_path = creation.source_png_path
            if not source_png_path:
                import re
                safe_theme = re.sub(r'[^a-zA-Z0-9]+', '_', creation.theme or "design").strip('_')
                if not safe_theme:
                    safe_theme = f"design_{creation.id}"
                source_png_path = f"/static/creation_{creation.id}/{safe_theme}_source.png"
                creation.source_png_path = source_png_path
                db.commit()
            local_path = source_png_path.replace("/static/", STORAGE_DIR + "/")
# MISSING LINE 2080

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
# MISSING LINE 2082

        canvas_data_raw = req.canvas_data or req.canvasData
        if not canvas_data_raw:
            raise HTTPException(status_code=400, detail="Missing canvasData or canvas_data")
        header, encoded = canvas_data_raw.split(",", 1)
        data = base64.b64decode(encoded)
# MISSING LINE 2088

        def _write_bytes():
            with open(local_path, "wb") as f:
                f.write(data)
        await asyncio.to_thread(_write_bytes)
# MISSING LINE 2093

        asset_type = req.asset_type or "master_stencil"
# MISSING LINE 2095

        # Enforce pipeline status to "processing" to trigger the spinner/polling on UI
        creation.status = "processing"
        creation.current_step = "Régénération des assets..."
        db.commit()
# MISSING LINE 2100

        # Schedule the heavy processing as a background task
        background_tasks.add_task(
            run_downstream_pipeline_operations,
            creation_id=creation.id,
            local_path=local_path,
            asset_type=asset_type
        )
# MISSING LINE 2108

        return {
            "status": "processing",
            "message": "Workspace saved. Downstream generation started in background."
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
