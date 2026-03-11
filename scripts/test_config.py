
"""
配置测试脚本
测试配置加载、命名规则渲染和目录路径生成
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from jinja2 import Template

from app.core.config import config_manager
from app.core.paths import paths


def test_config_loading():
    """测试配置加载"""
    logger.info("=" * 50)
    logger.info("测试1: 配置加载")
    logger.info("=" * 50)

    try:
        # 加载配置
        config = config_manager.load()

        # 测试基础配置
        logger.info(f"应用名称: {config.app.name}")
        logger.info(f"应用版本: {config.app.version}")
        logger.info(f"调试模式: {config.app.debug}")

        # 测试服务器配置
        logger.info(f"服务器地址: {config.server.host}:{config.server.port}")
        logger.info(f"工作进程数: {config.server.workers}")

        # 测试数据库配置
        logger.info(f"数据库路径: {config.database.url}")

        # 测试日志配置
        logger.info(f"日志级别: {config.logging.level}")
        logger.info(f"日志格式: {config.logging.format}")

        # 测试扫描配置
        logger.info(f"扫描路径: {config.scanner.watch_paths}")
        logger.info(f"递归扫描: {config.scanner.recursive}")

        # 测试识别配置
        logger.info(f"识别模式: {config.recognition.mode}")
        logger.info(f"TMDB API Key: {'已配置' if config.recognition.sources.tmdb.api_key else '未配置'}")

        # 测试整理配置
        logger.info(f"整理模式: {config.organize.mode}")
        logger.info(f"整理动作: {config.organize.action_type}")
        logger.info(f"冲突策略: {config.organize.conflict_strategy}")

        logger.success("✅ 配置加载测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 配置加载失败: {e}")
        return False


def test_naming_rules():
    """测试命名规则加载和渲染"""
    logger.info("=" * 50)
    logger.info("测试2: 命名规则渲染")
    logger.info("=" * 50)

    try:
        # 加载命名规则配置
        naming_config = config_manager.config.naming_rules

        # 测试电影命名规则
        logger.info("\n电影命名规则测试:")
        movie_template = naming_config.movie.default
        logger.info(f"默认模板: {movie_template}")

        # 渲染电影命名
        template = Template(movie_template)
        test_vars = {
            'title': 'The Matrix',
            'original_title': 'The Matrix',
            'year': 1999,
            'season': None,
            'episode': None,
            'quality': '1080p',
            'source': 'BluRay',
            'codec': 'x264',
            'audio': 'AAC',
            'release_group': 'SPARKS',
            'language': 'en',
            'audio_language': 'en',
            'subtitle_language': 'zh',
            'country': 'US',
            'region': 'US',
            'resolution': '1920x1080',
            'bitdepth': '8bit',
            'hdr': '',
            'primary_category': 'movie',
            'sub_category': 'sci-fi',
            'genre': 'Action,Sci-Fi',
            'file_name': 'The.Matrix.1999.1080p.BluRay.x264.mkv',
            'file_stem': 'The.Matrix.1999.1080p.BluRay.x264',
            'file_extension': 'mkv',
            'content_rating': 'R',
            'studio': 'Warner Bros.'
        }

        rendered_name = template.render(**test_vars)
        logger.info(f"渲染结果: {rendered_name}")

        # 测试电视剧命名规则
        logger.info("
电视剧命名规则测试:")
        tv_template = naming_config.tv.default
        logger.info(f"默认模板: {tv_template}")

        # 渲染电视剧命名
        tv_vars = test_vars.copy()
        tv_vars.update({
            'title': 'Breaking Bad',
            'season': 1,
            'episode': 1,
            'episode_title': 'Pilot',
            'primary_category': 'tv',
            'sub_category': 'drama',
            'genre': 'Crime,Drama'
        })

        template = Template(tv_template)
        rendered_name = template.render(**tv_vars)
        logger.info(f"渲染结果: {rendered_name}")

        # 测试动漫命名规则
        logger.info("
动漫命名规则测试:")
        anime_template = naming_config.anime.default
        logger.info(f"默认模板: {anime_template}")

        # 渲染动漫命名
        anime_vars = test_vars.copy()
        anime_vars.update({
            'title': 'Attack on Titan',
            'episode': 1,
            'primary_category': 'anime',
            'sub_category': 'action',
            'genre': 'Action',
            'release_group': 'SubsPlease'
        })

        template = Template(anime_template)
        rendered_name = template.render(**anime_vars)
        logger.info(f"渲染结果: {rendered_name}")

        logger.success("✅ 命名规则渲染测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 命名规则渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_directory_rules():
    """测试目录规则渲染"""
    logger.info("=" * 50)
    logger.info("测试3: 目录路径生成")
    logger.info("=" * 50)

    try:
        naming_config = config_manager.config.naming_rules

        # 测试电影目录
        logger.info("
电影目录测试:")
        movie_dir_template = naming_config.directory_rules.movie
        logger.info(f"模板: {movie_dir_template}")

        template = Template(movie_dir_template)
        test_vars = {
            'title': 'The Matrix',
            'year': 1999,
            'season': None,
            'episode': None,
            'primary_category': 'movie',
            'sub_category': 'sci-fi'
        }

        rendered_dir = template.render(**test_vars)
        logger.info(f"渲染结果: {rendered_dir}")

        # 测试电视剧目录
        logger.info("
电视剧目录测试:")
        tv_dir_template = naming_config.directory_rules.tv
        logger.info(f"模板: {tv_dir_template}")

        tv_vars = test_vars.copy()
        tv_vars.update({
            'title': 'Breaking Bad',
            'season': 1,
            'primary_category': 'tv',
            'sub_category': 'drama'
        })

        template = Template(tv_dir_template)
        rendered_dir = template.render(**tv_vars)
        logger.info(f"渲染结果: {rendered_dir}")

        # 测试动漫目录
        logger.info("
动漫目录测试:")
        anime_dir_template = naming_config.directory_rules.anime
        logger.info(f"模板: {anime_dir_template}")

        anime_vars = test_vars.copy()
        anime_vars.update({
            'title': 'Attack on Titan',
            'primary_category': 'anime',
            'sub_category': 'action'
        })

        template = Template(anime_dir_template)
        rendered_dir = template.render(**anime_vars)
        logger.info(f"渲染结果: {rendered_dir}")

        # 测试未识别文件目录
        logger.info("
未识别文件目录测试:")
        undefined_dir_template = naming_config.directory_rules.undefined
        logger.info(f"模板: {undefined_dir_template}")

        undefined_vars = test_vars.copy()
        undefined_vars.update({
            'sub_category': 'pending',
            'file_name': 'Unknown.File.2024.mkv'
        })

        template = Template(undefined_dir_template)
        rendered_dir = template.render(**undefined_vars)
        logger.info(f"渲染结果: {rendered_dir}")

        logger.success("✅ 目录路径生成测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 目录路径生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_subtitle_naming():
    """测试字幕命名规则"""
    logger.info("=" * 50)
    logger.info("测试4: 字幕文件命名")
    logger.info("=" * 50)

    try:
        naming_config = config_manager.config.naming_rules
        subtitle_template = naming_config.subtitle_naming.pattern

        logger.info(f"字幕命名模板: {subtitle_template}")

        # 测试不同语言
        test_cases = [
            {'language': 'zh', 'ext': '.srt', 'media_name': 'The Matrix (1999)'},
            {'language': 'en', 'ext': '.ass', 'media_name': 'The Matrix (1999)'},
            {'language': 'ja', 'ext': '.srt', 'media_name': 'The Matrix (1999)'},
        ]

        for case in test_cases:
            template = Template(subtitle_template)
            rendered = template.render(
                media_name=case['media_name'],
                language=case['language'],
                ext=case['ext']
            )
            logger.info(f"{case['language']}: {rendered}")

        logger.success("✅ 字幕命名规则测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 字幕命名规则测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_path_resolution():
    """测试路径解析功能"""
    logger.info("=" * 50)
    logger.info("测试5: 路径解析")
    logger.info("=" * 50)

    try:
        # 测试相对路径解析
        test_paths = [
            './data/db',
            './logs',
            './config',
            'D:/Downloads',
            'E:/Media/Movies'
        ]

        for path in test_paths:
            resolved = paths.get_path(path)
            logger.info(f"{path} -> {resolved}")

        # 测试目录创建
        logger.info("
测试目录创建:")
        test_dirs = [
            './data/test',
            './logs/test',
            './temp/test'
        ]

        for dir_path in test_dirs:
            created_dir = paths.ensure_dir(dir_path)
            logger.info(f"创建目录: {created_dir}")

        logger.success("✅ 路径解析测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 路径解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    logger.info("
" + "=" * 50)
    logger.info("MediaService 配置测试")
    logger.info("=" * 50 + "
")

    # 运行所有测试
    results = {
        "配置加载": test_config_loading(),
        "命名规则渲染": test_naming_rules(),
        "目录路径生成": test_directory_rules(),
        "字幕命名规则": test_subtitle_naming(),
        "路径解析": test_path_resolution()
    }

    # 汇总结果
    logger.info("
" + "=" * 50)
    logger.info("测试结果汇总")
    logger.info("=" * 50)

    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")

    # 总体结果
    all_passed = all(results.values())
    if all_passed:
        logger.success("
🎉 所有测试通过！配置系统工作正常。")
        logger.info("
下一步：")
        logger.info("1. 启动服务: python app/main.py")
        logger.info("2. 访问Web界面: http://localhost:8000")
        logger.info("3. 查看API文档: http://localhost:8000/docs")
        return 0
    else:
        logger.error("
⚠️ 部分测试失败，请检查配置文件。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
