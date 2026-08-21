import os
import unittest
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PIL import Image

from app.database import Base
from app.models import Setting, Creation

class TestEtsyLaserAutomation(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Setup in-memory SQLite database for testing
        cls.engine = create_engine("sqlite:///:memory:")
        cls.SessionLocal = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.query(Setting).delete()
        self.db.query(Creation).delete()
        self.db.commit()
        self.db.close()

    def test_settings_initialization(self):
        """Test default settings rows can be created and queried."""
        settings = Setting(
            openai_key="test_openai",
            default_price=3.5,
            default_quantity=100,
            default_status="active"
        )
        self.db.add(settings)
        self.db.commit()

        queried = self.db.query(Setting).first()
        self.assertIsNotNone(queried)
        self.assertEqual(queried.openai_key, "test_openai")
        self.assertEqual(queried.default_price, 3.5)
        self.assertEqual(queried.default_quantity, 100)
        self.assertEqual(queried.default_status, "active")

    def test_creation_record(self):
        """Test creations database row persistence and attributes."""
        creation = Creation(
            theme="Mandala Wolf",
            title_fr="Loup Mandala Découpe Bois",
            title_en="Mandala Wolf Laser Cut File",
            is_published_etsy=False
        )
        self.db.add(creation)
        self.db.commit()

        queried = self.db.query(Creation).first()
        self.assertIsNotNone(queried)
        self.assertEqual(queried.theme, "Mandala Wolf")
        self.assertEqual(queried.title_fr, "Loup Mandala Découpe Bois")
        self.assertFalse(queried.is_published_etsy)

    def test_fallback_vectorization(self):
        """Test the pure Python SVG and DXF tracing fallback generators."""
        from app.services.vector import fallback_png_to_svg, fallback_png_to_dxf
        
        # Create a simple test PNG in memory
        from PIL import ImageDraw
        img = Image.new("L", (10, 10), 255)
        draw = ImageDraw.Draw(img)
        draw.rectangle([2, 2, 7, 7], fill=0) # Black square in center
        
        test_png = "test_source.png"
        test_svg = "test_fallback.svg"
        test_dxf = "test_fallback.dxf"
        
        try:
            img.save(test_png)
            
            # Test SVG Fallback
            fallback_png_to_svg(test_png, test_svg)
            self.assertTrue(os.path.exists(test_svg))
            with open(test_svg, "r") as f:
                content = f.read()
                self.assertIn("<svg", content)
                self.assertIn("path d=", content)
                
            # Test DXF Fallback
            fallback_png_to_dxf(test_png, test_dxf)
            self.assertTrue(os.path.exists(test_dxf))
            with open(test_dxf, "r") as f:
                content = f.read()
                self.assertIn("HEADER", content)
                self.assertIn("LINE", content)
                self.assertIn("EOF", content)
                
        finally:
            # Cleanup test files
            for p in [test_png, test_svg, test_dxf]:
                if os.path.exists(p):
                    os.remove(p)

    def test_transparent_png_and_pdf_generation(self):
        """Test high-quality transparent PNG conversion (preserving colors) and PNG-to-PDF conversion."""
        from app.services.image import convert_to_transparent_png, png_to_pdf
        
        # Create a colored test image (e.g. red rectangle on a white background)
        img = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([2, 2, 7, 7], fill=(255, 0, 0, 255)) # Red square
        
        test_src = "test_src.png"
        test_transparent = "test_transparent.png"
        test_pdf = "test_out.pdf"
        
        try:
            img.save(test_src)
            
            # Run transparent conversion
            convert_to_transparent_png(test_src, test_transparent, scale_factor=2)
            self.assertTrue(os.path.exists(test_transparent))
            
            # Check size is scaled (10 * 2 = 20)
            with Image.open(test_transparent) as t_img:
                self.assertEqual(t_img.size, (20, 20))
                # Check that transparency is applied on white area (e.g., pixel (0,0))
                pixel_white_bg = t_img.getpixel((0, 0))
                self.assertEqual(pixel_white_bg[3], 0) # Alpha channel should be 0
                
                # Check that red color is preserved (e.g. pixel in center, scaled to (10,10))
                pixel_red = t_img.getpixel((10, 10))
                self.assertEqual(pixel_red[0], 255) # Red
                self.assertEqual(pixel_red[1], 0)   # Green
                self.assertEqual(pixel_red[2], 0)   # Blue
                self.assertEqual(pixel_red[3], 255) # Alpha opaque
                
            # Run PNG to PDF conversion
            png_to_pdf(test_transparent, test_pdf)
            self.assertTrue(os.path.exists(test_pdf))
            
        finally:
            for p in [test_src, test_transparent, test_pdf]:
                if os.path.exists(p):
                    os.remove(p)

    def test_real_mockup_with_tp_overlay(self):
        """Test create_real_mockup with apply_tp_overlay=True/False."""
        from app.services.mockup_engine import create_real_mockup
        
        # Create dummy stencil and background
        stencil = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(stencil)
        draw.rectangle([40, 40, 60, 60], fill=(0, 0, 0, 255)) # small black square
        bg = Image.new("RGBA", (100, 100), (255, 255, 255, 255)) # White bg
        
        test_stencil = "test_stencil.png"
        test_bg = "test_bg.png"
        test_out_false = "test_out_false.jpg"
        test_out_true = "test_out_true.jpg"
        
        from unittest.mock import patch
        
        try:
            stencil.save(test_stencil)
            bg.save(test_bg)

            # Test with apply_tp_overlay=False
            create_real_mockup(test_stencil, test_bg, test_out_false, apply_tp_overlay=False)
            self.assertTrue(os.path.exists(test_out_false))

            # Test with apply_tp_overlay=True
            create_real_mockup(test_stencil, test_bg, test_out_true, apply_tp_overlay=True)
            self.assertTrue(os.path.exists(test_out_true))

            
        finally:
            for p in [test_stencil, test_bg, test_out_false, test_out_true]:
                if os.path.exists(p):
                    os.remove(p)

    def test_inkscape_wireframe_cleaning(self):
        """Test that png_to_svg cleans up the SVG with Inkscape into a wireframe if requested."""
        from app.services.vector import png_to_svg, verify_binary
        
        test_png = "test_source_wireframe.png"
        test_svg = "test_cleaned.svg"
        
        from PIL import Image, ImageDraw
        img = Image.new("L", (100, 100), 255)
        draw = ImageDraw.Draw(img)
        draw.ellipse([20, 20, 80, 80], fill=0) # Black circle
        
        try:
            img.save(test_png)
            potrace_bin = "/opt/homebrew/bin/potrace" if verify_binary("/opt/homebrew/bin/potrace") else "potrace"
            inkscape_bin = "/opt/homebrew/bin/inkscape" if verify_binary("/opt/homebrew/bin/inkscape") else "inkscape"
            
            png_to_svg(potrace_bin, test_png, test_svg, inkscape_bin)
            self.assertTrue(os.path.exists(test_svg))
        finally:
            for p in [test_png, test_svg]:
                if os.path.exists(p):
                    os.remove(p)

    def test_adaptive_local_binarization(self):
        """Test local adaptive thresholding (Sauvola/Bradley) preserves fine details."""
        from app.services.vector import local_adaptive_binarize
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.line([(10, 10), (190, 190)], fill=(30, 30, 30), width=2)
        bw = local_adaptive_binarize(img)
        self.assertEqual(bw.size, (200, 200))
        # Center line pixel should be black (0)
        self.assertEqual(bw.getpixel((100, 100)), 0)
        # Background pixel should be white (255)
        self.assertEqual(bw.getpixel((10, 100)), 255)

    def test_svg_node_simplification(self):
        """Test SVG path node optimization with Douglas-Peucker."""
        from app.services.vector import simplify_svg_paths
        test_svg = "test_nodes.svg"
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path d="M 0,0 L 1,0.05 L 2,-0.05 L 3,0.02 L 10,0 L 10,10 L 0,10 Z" fill="#000000"/>
</svg>'''
        try:
            with open(test_svg, "w") as f:
                f.write(svg_content)
            success = simplify_svg_paths(test_svg, test_svg, tolerance=0.2)
            self.assertTrue(success)
            with open(test_svg, "r") as f:
                content = f.read()
            self.assertIn("<path", content)
            self.assertIn('d="M', content)
        finally:
            if os.path.exists(test_svg):
                os.remove(test_svg)

    def test_vector_export_formats_eps_pdf_ai(self):
        """Test native vector export for EPS, PDF, and AI using svglib and ReportLab."""
        from app.services.export_formats import svg_to_eps, svg_to_pdf, svg_to_ai
        test_svg = "test_vector.svg"
        test_eps = "test_vector.eps"
        test_pdf = "test_vector.pdf"
        test_ai = "test_vector.ai"

        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <rect x="20" y="20" width="160" height="160" fill="black"/>
</svg>'''
        try:
            with open(test_svg, "w") as f:
                f.write(svg_content)

            self.assertTrue(svg_to_eps("inkscape", test_svg, test_eps))
            self.assertTrue(os.path.exists(test_eps))
            self.assertGreater(os.path.getsize(test_eps), 100)

            self.assertTrue(svg_to_pdf("inkscape", test_svg, test_pdf))
            self.assertTrue(os.path.exists(test_pdf))
            self.assertGreater(os.path.getsize(test_pdf), 100)

            self.assertTrue(svg_to_ai("inkscape", test_svg, test_ai))
            self.assertTrue(os.path.exists(test_ai))
            self.assertGreater(os.path.getsize(test_ai), 100)
        finally:
            for p in [test_svg, test_eps, test_pdf, test_ai]:
                if os.path.exists(p):
                    os.remove(p)

    def test_split_multielement_image(self):
        """Test bundle segmentation with 2D spatial sorting and padding."""
        from app.services.image_engine import split_multielement_image
        from PIL import Image, ImageDraw
        import tempfile

        img = Image.new("RGB", (600, 600), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        # 4 distinct squares in 2x2 grid
        draw.rectangle([50, 50, 200, 200], fill=(0, 0, 0))
        draw.rectangle([350, 50, 500, 200], fill=(0, 0, 0))
        draw.rectangle([50, 350, 200, 500], fill=(0, 0, 0))
        draw.rectangle([350, 350, 500, 500], fill=(0, 0, 0))

        test_bundle = "test_bundle.png"
        test_out_dir = "test_split_out"
        try:
            img.save(test_bundle)
            paths = split_multielement_image(test_bundle, test_out_dir, bundle_size=4)
            self.assertEqual(len(paths), 4)
            for p in paths:
                self.assertTrue(os.path.exists(p))
                with Image.open(p) as elem_img:
                    self.assertEqual(elem_img.size, (1024, 1024))
        finally:
            if os.path.exists(test_bundle):
                os.remove(test_bundle)
            if os.path.exists(test_out_dir):
                shutil.rmtree(test_out_dir)

    def test_real_layer_compositing_mockup(self):
        """Test real layer-based compositing with drop shadows without AI hallucinations."""
        from app.services.mockup_engine import create_real_layer_compositing
        from PIL import Image, ImageDraw
        stencil = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
        draw = ImageDraw.Draw(stencil)
        draw.ellipse([40, 40, 160, 160], fill=(0, 0, 0, 255))

        test_stencil = "test_real_stencil.png"
        test_out = "test_real_comp.jpg"
        try:
            stencil.save(test_stencil)
            res = create_real_layer_compositing(
                stencil_path=test_stencil,
                output_path=test_out,
                style="classic_living_room",
                apply_watermark=False
            )
            self.assertTrue(os.path.exists(test_out))
            self.assertGreater(os.path.getsize(test_out), 1000)
            with Image.open(test_out) as img:
                self.assertEqual(img.size, (1200, 1200))
        finally:
            for p in [test_stencil, test_out]:
                if os.path.exists(p):
                    os.remove(p)

    def test_etsy_standard_mockup_pack_4_images(self):
        """Test generation of the standardized 4-image Etsy pack."""
        from app.services.mockup_engine import generate_etsy_standard_mockup_pack
        from PIL import Image, ImageDraw
        import tempfile

        stencil = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
        draw = ImageDraw.Draw(stencil)
        draw.rectangle([50, 50, 150, 150], fill=(0, 0, 0, 255))

        test_stencil = "test_pack_stencil.png"
        out_dir = "test_pack_out"
        try:
            stencil.save(test_stencil)
            pack = generate_etsy_standard_mockup_pack(
                stencil_path=test_stencil,
                output_dir=out_dir,
                theme="Mandala Lion",
                bundle_size=1,
                apply_watermark=True,
                watermark_text="digitalfilesbymop"
            )
            self.assertEqual(len(pack["all_paths"]), 4)
            for p in pack["all_paths"]:
                self.assertTrue(os.path.exists(p))
                self.assertGreater(os.path.getsize(p), 1000)
                with Image.open(p) as img:
                    self.assertEqual(img.size, (1200, 1200))
        finally:
            if os.path.exists(test_stencil):
                os.remove(test_stencil)
            if os.path.exists(out_dir):
                shutil.rmtree(out_dir)

    def test_anti_theft_watermark_toggle(self):
        """Test watermark application when toggled."""
        from app.services.mockup_engine import apply_watermark_to_image
        from PIL import Image
        base = Image.new("RGB", (400, 400), (100, 100, 100))
        wm = apply_watermark_to_image(base, watermark_text="digitalfilesbymop", opacity=0.3)
        self.assertEqual(wm.size, (400, 400))
        self.assertNotEqual(list(wm.getdata()), list(base.getdata()))

    def test_creation_asset_relational_model(self):
        """Test CreationAsset relational table creation and linkage."""
        from app.models import Creation, CreationAsset

        creation = Creation(theme="Test Asset Theme", status="pending")
        self.db.add(creation)
        self.db.commit()
        self.db.refresh(creation)

        asset1 = CreationAsset(
            creation_id=creation.id,
            asset_type="svg",
            file_path="/static/test.svg",
            filename="test.svg"
        )
        asset2 = CreationAsset(
            creation_id=creation.id,
            asset_type="dxf",
            file_path="/static/test.dxf",
            filename="test.dxf"
        )
        self.db.add_all([asset1, asset2])
        self.db.commit()
        self.db.refresh(creation)

        self.assertEqual(len(creation.assets), 2)
        types = [a.asset_type for a in creation.assets]
        self.assertIn("svg", types)
        self.assertIn("dxf", types)


    def test_storage_stats_and_purge(self):
        """Test /api/settings/storage-stats and /api/settings/purge-storage endpoints."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        res_stats = client.get("/api/settings/storage-stats")
        self.assertEqual(res_stats.status_code, 200)
        data = res_stats.json()
        self.assertIn("total_size_mb", data)
        self.assertIn("temp_files_count", data)

        res_purge = client.post("/api/settings/purge-storage")
        self.assertEqual(res_purge.status_code, 200)
        purge_data = res_purge.json()
        self.assertEqual(purge_data.get("status"), "success")
        self.assertIn("deleted_files_count", purge_data)

    def test_detect_floating_islands_and_overlay(self):
        """Test computer vision detection of disconnected stencil islands."""
        from app.services.svg_analyzer import detect_floating_islands, generate_islands_overlay
        from PIL import Image, ImageDraw

        test_img_path = "test_islands.png"
        test_overlay_path = "test_islands_overlay.png"

        # Create white background with main black body and 2 floating black pieces
        img = Image.new("RGB", (300, 300), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Main body (large rectangle)
        draw.rectangle([50, 50, 250, 250], fill=(0, 0, 0))
        # Cut interior hole so there is empty space
        draw.rectangle([80, 80, 220, 220], fill=(255, 255, 255))
        # Island 1 (floating square in the center hole)
        draw.rectangle([130, 130, 170, 170], fill=(0, 0, 0))
        # Island 2 (floating square outside)
        draw.rectangle([10, 10, 30, 30], fill=(0, 0, 0))
        img.save(test_img_path)

        try:
            analysis = detect_floating_islands(test_img_path, min_island_area=15)
            self.assertEqual(analysis["island_count"], 2)
            self.assertEqual(len(analysis["islands"]), 2)

            overlay = generate_islands_overlay(test_img_path, test_overlay_path, analysis["islands"])
            self.assertTrue(os.path.exists(overlay))
            self.assertGreater(os.path.getsize(overlay), 500)
        finally:
            if os.path.exists(test_img_path):
                os.remove(test_img_path)
            if os.path.exists(test_overlay_path):
                os.remove(test_overlay_path)

    def test_auto_bridge_stencil(self):
        """Test geometric 1-click auto-bridging of floating islands."""
        from app.services.svg_analyzer import detect_floating_islands, auto_bridge_stencil
        from PIL import Image, ImageDraw

        test_img_path = "test_bridge_in.png"
        test_bridged_path = "test_bridge_out.png"

        img = Image.new("RGB", (300, 300), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Main body
        draw.rectangle([50, 50, 250, 250], fill=(0, 0, 0))
        draw.rectangle([80, 80, 220, 220], fill=(255, 255, 255))
        # Island 1 in the middle
        draw.rectangle([130, 130, 170, 170], fill=(0, 0, 0))
        img.save(test_img_path)

        try:
            # 1. Before auto-bridge -> 1 floating island
            before = detect_floating_islands(test_img_path)
            self.assertEqual(before["island_count"], 1)

            # 2. Run auto-bridge
            res = auto_bridge_stencil(test_img_path, test_bridged_path, bridge_width=6)
            self.assertTrue(res["success"])
            self.assertEqual(res["bridges_added"], 1)

            # 3. After auto-bridge -> 0 floating islands (fully connected!)
            after = detect_floating_islands(test_bridged_path)
            self.assertEqual(after["island_count"], 0)
        finally:
            if os.path.exists(test_img_path):
                os.remove(test_img_path)
            if os.path.exists(test_bridged_path):
                os.remove(test_bridged_path)

if __name__ == "__main__":
    import os
    from PIL import Image
    unittest.main()




