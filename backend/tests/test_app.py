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

if __name__ == "__main__":
    import os
    from PIL import Image
    unittest.main()
