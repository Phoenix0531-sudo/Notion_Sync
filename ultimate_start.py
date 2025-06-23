#!/usr/bin/env python3
"""
终极启动脚本 - 解决所有已知的导入和类型注解问题
"""

import sys
import os
from pathlib import Path

def comprehensive_fix():
    """全面修复导入和类型注解问题。"""
    print("🔧 应用全面修复...")
    
    # 1. 修复 typing 导入
    import typing
    import builtins
    
    # 常用类型
    typing_imports = {
        'List': typing.List,
        'Dict': typing.Dict, 
        'Tuple': typing.Tuple,
        'Optional': typing.Optional,
        'Union': typing.Union,
        'Any': typing.Any,
        'Callable': typing.Callable,
        'Set': typing.Set,
        'Generator': typing.Generator
    }
    
    for name, type_obj in typing_imports.items():
        setattr(builtins, name, type_obj)
    
    # 2. 修复 pathlib 导入
    from pathlib import Path as PathlibPath
    setattr(builtins, 'Path', PathlibPath)
    
    # 3. 修复 datetime 导入
    from datetime import datetime
    setattr(builtins, 'datetime', datetime)
    
    print("✅ 类型注解修复完成")

def setup_environment():
    """设置环境。"""
    print("🔧 设置环境...")
    
    # 应用修复
    comprehensive_fix()
    
    # 设置 Python 路径
    src_dir = Path(__file__).parent / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))
        print(f"✅ 已添加 src 目录到路径: {src_dir}")
        return True
    else:
        print(f"❌ 找不到 src 目录: {src_dir}")
        return False

def patch_modules():
    """预先修补可能有问题的模块。"""
    print("🩹 预先修补模块...")
    
    try:
        # 确保所有必要的导入都可用
        import sys
        import os
        from pathlib import Path
        from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
        from datetime import datetime
        
        # 将这些添加到全局命名空间
        globals().update({
            'Path': Path,
            'Dict': Dict,
            'List': List,
            'Optional': Optional,
            'Any': Any,
            'Tuple': Tuple,
            'Set': Set,
            'Union': Union,
            'Callable': Callable,
            'datetime': datetime
        })
        
        print("✅ 模块修补完成")
        return True
    except Exception as e:
        print(f"❌ 模块修补失败: {e}")
        return False

def main():
    print("🚀 终极启动 Notion 同步工具...")
    
    # 预先修补
    if not patch_modules():
        return 1
    
    # 设置环境
    if not setup_environment():
        return 1
    
    # 尝试启动应用程序
    try:
        print("正在导入主模块...")
        
        # 在导入前再次确保类型可用
        import builtins
        from pathlib import Path as PathlibPath
        from typing import Dict, List, Optional, Any
        
        setattr(builtins, 'Path', PathlibPath)
        setattr(builtins, 'Dict', Dict)
        setattr(builtins, 'List', List)
        setattr(builtins, 'Optional', Optional)
        setattr(builtins, 'Any', Any)
        
        from notion_sync.main import main as app_main
        
        print("正在启动应用程序...")
        exit_code = app_main()
        
        print(f"应用程序退出，退出码: {exit_code}")
        return exit_code
        
    except NameError as e:
        print(f"❌ 类型注解错误: {e}")
        
        # 尝试更激进的修复
        print("尝试激进修复...")
        try:
            # 直接修改模块的全局命名空间
            import notion_sync.models.file_system
            import notion_sync.utils.settings_manager
            
            # 为这些模块添加缺失的类型
            from pathlib import Path as PathlibPath
            from typing import Dict, List, Optional, Any
            
            notion_sync.models.file_system.Path = PathlibPath
            notion_sync.utils.settings_manager.List = List
            notion_sync.utils.settings_manager.Dict = Dict
            
            # 重新尝试导入
            from notion_sync.main import main as app_main
            return app_main()
            
        except Exception as retry_error:
            print(f"激进修复也失败了: {retry_error}")
            return 1
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("\n可能的解决方案:")
        print("1. 检查依赖是否完整安装")
        print("2. 运行: pip install PySide6 SQLAlchemy aiohttp watchdog keyring requests")
        return 1
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n详细错误信息:")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
