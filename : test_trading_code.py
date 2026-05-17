import os
import json
import subprocess
import tempfile
import sys
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class CodeTester:
    """ระบบตรวจสอบโค้ด"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.test_results = []
    
    def check_syntax(self, code):
        """Test 1: เช็คไวยากรณ์"""
        print("🔍 Test 1: ตรวจสอบไวยากรณ์...")
        try:
            compile(code, '<string>', 'exec')
            print("✅ ไวยากรณ์ถูกต้อง\n")
            return True
        except SyntaxError as e:
            error_msg = f"❌ Syntax Error: {str(e)}"
            print(error_msg)
            self.errors.append(error_msg)
            return False
    
    def run_code(self, code, timeout=10):
        """Test 2: รันโค้ด"""
        print("🔍 Test 2: รันโค้ด...")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                print("✅ รันได้สำเร็จ\n")
                print("📊 Output:")
                print(result.stdout)
                print()
                return {
                    "success": True,
                    "output": result.stdout
                }
            else:
                error_msg = f"❌ Runtime Error:\n{result.stderr}"
                print(error_msg)
                print()
                self.errors.append(error_msg)
                return {
                    "success": False,
                    "error": result.stderr
                }
        
        except subprocess.TimeoutExpired:
            error_msg = f"❌ Timeout: โค้ดรันนาน > {timeout} วินาที"
            print(error_msg)
            print()
            self.errors.append(error_msg)
            return {
                "success": False,
                "error": "Timeout"
            }
        
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            print(error_msg)
            print()
            self.errors.append(error_msg)
            return {
                "success": False,
                "error": str(e)
            }
        
        finally:
            import os as os_module
            try:
                os_module.remove(temp_file)
            except:
                pass
    
    def check_logic(self, code):
        """Test 3: AI วิเคราะห์ Logic"""
        print("🔍 Test 3: ตรวจสอบ Logic (AI ช่วย)...")
        
        prompt = f"""
วิเคราะห์โค้ด Python นี้ เพื่อหาจุดบกพร่อง:

```python
{code}
