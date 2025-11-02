# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import a2s
import random
from playwright.async_api import async_playwright
import platform
import textwrap
import requests
import os

class ServerStatusRenderer:
    def __init__(self):
        # 繼承 Status 插件的背景系統
        base_dir = os.path.dirname(__file__)
        self.background_paths = [
            os.path.join(base_dir, 'htmlmaterial/ba.txt')
        ]
        # 樣式設定
        self.config = {
            "botName": "伺服器狀態查詢",
            "HTML_setting": {
                "Backgroundblurs": 0, # 增加模糊度以提高可讀性
                "Backgroundcolor": "rgba(230, 215, 235, 0.692)",
                "dashboardTextColor1": "rgba(29,131,190,1)",
                "dashboardTextColor2": "rgba(149,40,180,1)",
                # 確保這些字體檔案存在於指定路徑
                "textfont1": "./font/Gugi-Regular.ttf",
                "textfont2": "./font/HachiMaruPop-Regular.ttf"
            }
        }

    def get_random_background(self):
        """從設定的路徑中選擇一個隨機背景。"""
        background_path = random.choice(self.background_paths)
        
        if background_path.startswith(('http://', 'https://')):
            return background_path
        elif background_path.endswith('.txt'):
            try:
                with open(background_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                return random.choice(lines).replace('\\', '/')
            except FileNotFoundError:
                return "https://placehold.co/1920x1080/E0D7EB/333333?text=Background+Not+Found"
        else:
            files = [f for f in os.listdir(background_path) 
                     if f.lower().endswith(('.jpg', '.png', '.gif', '.bmp'))]
            return os.path.join(background_path, random.choice(files)).replace('\\', '/')

    def rgba_to_hex(self, rgba):
        """將 RGBA 字串轉換為 HEX 顏色，忽略透明度。"""
        try:
            rgba = rgba.replace("rgba(", "").replace(")", "")
            r, g, b, _ = [int(float(x.strip())) for x in rgba.split(",")]
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return "#000000" # 備用顏色

    def generate_html(self, host, port, info, players):
        """產生帶有更新樣式的伺服器狀態 HTML。"""
        bg_image = self.get_random_background()
        player_list_html = self._format_players_html(players)
        platform_icon = "🖥️" if info.platform == "w" else "🐧" if info.platform == "l" else "👀"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        @font-face {{ font-family: Gugi; src: url('{self.config["HTML_setting"]["textfont1"]}'); }}
        @font-face {{ font-family: HachiMaruPop; src: url('{self.config["HTML_setting"]["textfont2"]}'); }}
        
        body {{
            margin: 0;
            padding: 0;
            font-family: HachiMaruPop, sans-serif;
            background-color: #f5f5f5;
        }}
        
        .status-container {{
            width: 100%;
            min-height: 100vh;
            position: relative;
            background-image: url('{bg_image}');
            background-size: cover;
            background-position: center;
            padding: 40px 20px;
            box-sizing: border-box;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .status-container::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            backdrop-filter: blur({self.config["HTML_setting"]["Backgroundblurs"]}px);
            background: {self.config["HTML_setting"]["Backgroundcolor"]};
            z-index: 1;
        }}
        
        .status-card {{
            position: relative;
            z-index: 2;
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .server-header {{
            display: flex;
            align-items: center;
            margin-bottom: 25px;
            border-bottom: 2px solid {self.rgba_to_hex(self.config["HTML_setting"]["dashboardTextColor1"])};
            padding-bottom: 20px;
        }}
        
        .server-icon {{
            font-size: 50px;
            margin-right: 20px;
            line-height: 1;
        }}
        
        .server-title h1 {{
            font-family: Gugi, sans-serif;
            font-size: 28px;
            color: {self.rgba_to_hex(self.config["HTML_setting"]["dashboardTextColor2"])};
            margin: 0 0 5px 0;
            word-break: break-all;
        }}

        .server-title div {{
            font-size: 16px;
            color: #333;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 18px;
            margin-bottom: 25px;
        }}
        
        .info-item {{
            display: flex;
            align-items: center;
            font-size: 18px;
            background: rgba(255, 255, 255, 0.5);
            padding: 12px;
            border-radius: 10px;
        }}
        
        .info-icon {{
            margin-right: 12px;
            font-size: 24px;
        }}

        /* MODIFICATION: Removed max-height and overflow-y to allow the list to fully expand for the screenshot */
        .player-list {{
            padding-right: 10px; /* keep padding for alignment */
        }}
        
        .player-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 15px;
            margin: 8px 0;
            background: rgba(0, 0, 0, 0.04);
            border-radius: 8px;
            transition: all 0.3s ease;
            border-left: 5px solid transparent;
        }}
        
        .player-item:hover {{
            background: rgba(0, 0, 0, 0.08);
            transform: translateX(5px);
            border-left: 5px solid {self.rgba_to_hex(self.config["HTML_setting"]["dashboardTextColor1"])};
        }}

        .player-name {{
            font-weight: bold;
            word-break: break-all;
            padding-right: 10px;
        }}

        .player-stats {{
            white-space: nowrap;
        }}
        
        .footer {{
            margin-top: 25px;
            text-align: center;
            font-size: 14px;
            color: #555;
            border-top: 1px solid #ddd;
            padding-top: 15px;
        }}
        
        .env-badge {{
            display: inline-block;
            padding: 4px 10px;
            background: {'#4CAF50' if info.platform == "w" else '#F44336'};
            color: white;
            border-radius: 12px;
            font-size: 14px;
            margin-left: 10px;
            vertical-align: middle;
        }}
    </style>
</head>
<body>
    <div class="status-container">
        <div class="status-card">
            <div class="server-header">
                <div class="server-icon">🌐</div>
                <div class="server-title">
                    <h1>{info.server_name[:30]}</h1>
                    <div>📍 {host}:{port} &nbsp;&nbsp;•&nbsp;&nbsp; ⏱️ 延遲: {info.ping*1000:.0f}ms</div>
                </div>
            </div>
            
            <div class="info-grid">
                <div class="info-item"><span class="info-icon">🗺️</span><span>地圖: {info.map_name}</span></div>
                <div class="info-item"><span class="info-icon">👥</span><span>玩家: {info.player_count}/{info.max_players}</span></div>
                <div class="info-item"><span class="info-icon">🎮</span><span>遊戲: {info.game}</span></div>
                <div class="info-item"><span class="info-icon">🛡️</span><span>VAC: {'✅ 啟用' if info.vac_enabled else '❌ 關閉'}</span></div>
                <div class="info-item"><span class="info-icon">🔒</span><span>密碼: {'🔐 有' if info.password_protected else '🔓 無'}</span></div>
                <div class="info-item">
                    <span class="info-icon">{platform_icon}</span>
                    <span>環境: <span class="env-badge">
                        {'Windows' if info.platform == "w" else 'Linux' if info.platform == "l" else '鴻蒙' if info.platform == "h" else 'Mac'}
                    </span></span>
                </div>
            </div>
            
            {player_list_html}
            
            <div class="footer">
                {self.config["botName"]} • 運行環境: {platform.system()} {platform.release()}
            </div>
        </div>
    </div>
</body>
</html>
        """
        return html

    def _format_players_html(self, players):
        """格式化 HTML 的玩家列表。"""
        if not players:
            return '<div style="text-align:center; padding:40px 20px; font-size: 18px;">🌙 暫無玩家在線</div>'
        
        sorted_players = sorted(players, key=lambda x: x.score, reverse=True)
        
        html = f"""
        <h3 class="players-title" style="font-family: Gugi; color: {self.rgba_to_hex(self.config['HTML_setting']['dashboardTextColor1'])}; border-top: 2px dashed #ccc; padding-top: 15px; margin-top: 20px;">
            👑 玩家列表 ({len(sorted_players)}人)
        </h3>
        <div class="player-list">
        """

        for idx, player in enumerate(sorted_players, 1):
            duration_str = self._format_duration(player.duration)
            player_name = player.name.strip() if player.name and player.name.strip() else "连接中..."
            html += f"""
            <div class="player-item">
                <span class="player-name">#{idx} {player_name[:20]}</span>
                <span class="player-stats">🎯 {player.score} &nbsp;&nbsp; ⏳ {duration_str}</span>
            </div>
            """
        
        html += "</div>"
        return html

    def _format_duration(self, seconds):
        """將遊戲時間從秒格式化為 HH:MM。"""
        try:
            s = int(seconds)
            if s < 0: s = 0 # 處理負的持續時間值
            hours, remainder = divmod(s, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}"
        except (ValueError, TypeError):
            return "00:00"

async def render_to_image(html, output="server_status.png"):
    """將 HTML 內容渲染為圖片檔案。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({ "width": 900, "height": 1080 })
        await page.set_content(html)
        card_element = await page.query_selector('.status-card')
        if card_element:
            await card_element.screenshot(path=output)
        else: 
            await page.screenshot(path=output, full_page=True)
        await browser.close()
    return output

async def render_to_image_url(url, output="server_status2.png"):
    """將 URL 渲染為圖片檔案。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=output, full_page=True)
        await browser.close()
    return output


@register("a2s_server_info", "伺服器查詢", "A2S協議伺服器狀態查詢插件", "2.0.0")
class A2SServerQuery(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.apikey = config.get('steam_api_key', None)
        self.renderer = ServerStatusRenderer()

    def format_response_text(self, host, port, info, players):
        """優化後的純文字佈局。"""
        header = "📊 伺 服 器 資 訊"
        
        base_info = textwrap.dedent(f"""
        ┌─── 基本資訊 ───
        │ 📍 位址: {host}:{port}
        │ ⏱️ 延遲: {info.ping*1000:.0f} ms
        │ 🔖 名稱: {info.server_name[:28]}
        │ 🗺️ 地圖: {info.map_name}
        │ 🎮 遊戲: {info.game}
        │ ⚙️ 類型: {'專用' if info.server_type == 'd' else '監聽'}
        │ 🛡️ VAC:  {'已啟用' if info.vac_enabled else '已關閉'}
        │ 🔑 密碼: {'有' if info.password_protected else '無'}
        └───
        """).strip()

        player_header = f"👥 玩 家 列 表 ({info.player_count}/{info.max_players})"
        player_list_str = ""
        if players:
            sorted_players = sorted(players, key=lambda x: x.score, reverse=True)
            for idx, p in enumerate(sorted_players, 1):
                duration_str = self.renderer._format_duration(p.duration)
                player_name = p.name.strip() if p.name and p.name.strip() else "连接中..."
                player_list_str += f" #{idx:<3} {player_name:<18.18s} | 🎯 {p.score:<6} | ⏳ {duration_str}\n"
        else:
            player_list_str += "🌙 暫無玩家在線\n"

        return f"{header}\n{base_info}\n\n{player_header}\n{'-'*25}\n{player_list_str.strip()}"

    async def _query_server(self, host, port, render_as_image=True):
        """通用查詢方法，可返回圖片路徑或文字。"""
        address = (host, port)
        info = await a2s.ainfo(address)
        players = await a2s.aplayers(address)

        if render_as_image:
            html = self.renderer.generate_html(host, port, info, players)
            image_path = await render_to_image(html)
            return image_path
        else:
            return self.format_response_text(host, port, info, players)

    @filter.command("ip")
    async def query_server_image(self, event: AstrMessageEvent, *, name: str):
        try:
            if ":" not in name:
                host = name
                port = 27015
            else:
                host, port_str = name.rsplit(":", 1)
                if not port_str.isdigit():
                    raise ValueError("端口必須是數字")
                
                port = int(port_str)
            yield event.plain_result("⏳ 正在查詢伺服器資訊並產生圖片...")
            image_path = await self._query_server(host, port, render_as_image=True)
            yield event.image_result(image_path)

        except Exception as e:
            logger.error(f"查詢失敗: {e}")
            yield event.plain_result(f"⛔ 查詢失敗: {e}")

    @filter.command("ipt")
    async def query_server_text(self, event: AstrMessageEvent, *, name: str):
        try:
            if ":" not in name:
                host = name
                port = 27015
            else:
                host, port_str = name.rsplit(":", 1)
                if not port_str.isdigit():
                    raise ValueError("端口必須是數字")
                
                port = int(port_str)
            yield event.plain_result("⏳ 正在查詢伺服器資訊...")
            response_text = await self._query_server(host, port, render_as_image=False)
            yield event.plain_result(response_text)

        except Exception as e:
            logger.error(f"查詢失敗: {e}")
            yield event.plain_result(f"⛔ 查詢失敗: {e}")

    async def _search_server_ip(self, game_id, keyword):
        API_KEY = self.apikey
        if not API_KEY or API_KEY == "" or API_KEY == "YOURSTEAMAPIKEY":
            raise ValueError("無效的STEAMAPIKEY！")
        url = f"https://api.steampowered.com/IGameServersService/GetServerList/v1/?key={API_KEY}&filter=\\appid\\{game_id}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ConnectionError(f"無法連接到 Steam API: {e}")
        
        data = response.json().get("response", {})
        servers = data.get("servers", [])

        if not servers:
            raise ValueError("⛔ 在該遊戲下未找到任何在線伺服器！")
        
        matched_servers = [
            server for server in servers
            if keyword.lower() in server.get("name", "").lower()
        ]
        
        if not matched_servers:
            raise ValueError(f"🤷 未找到名稱包含 '{keyword}' 的伺服器")
        
        host, port = matched_servers[0].get("addr").rsplit(":", 1)
        return host, int(port)


            
    @filter.command("find")
    async def search_server(self, event: AstrMessageEvent, *, name: str):
        try:
            if "|" not in name or not name:
                yield event.plain_result("格式: /find 游戏AppID|服务器名称")
                return
                
            game, keyword = name.rsplit("|", 1)
            
            host, port = await self._search_server_ip(game, keyword)
            image_path = await self._query_server(host, int(port))
            yield event.image_result(image_path)
        except Exception as e:
            logger.error(f"查询失败: {e}")
            yield event.plain_result(
                "⛔ 查询返回无结果！"
            )
            
    @filter.command("findt")
    async def search_text_server(self, event: AstrMessageEvent, *, name: str):
        try:
            if "|" not in name or not name:
                yield event.plain_result("格式: /find 游戏AppID|服务器名称")
                return
                
            game, keyword = name.rsplit("|", 1)
            
            host, port = await self._search_server_ip(game, keyword)
            address = host, int(port)
            info = await a2s.ainfo(address)
            players = await a2s.aplayers(address)
            yield event.plain_result(self.format_response(host, port, info, players))
        except Exception as e:
            logger.error(f"查询失败: {e}")
            yield event.plain_result(
                "⛔ 查询返回无结果！"
            )

    @filter.llm_tool("find_steam_game_server")
    async def find_server_ip(self, event: AstrMessageEvent, steamappid: str, name: str):
        """Find a Steam game server by its name, returning the IP and port.
        If multiple servers are found, return the first one.
        Use get_ip_a2s_server_info the query server information if game support a2s query.
        If user not provided which game, treat it as Garry's Mod(4000)
        
        Args:
            steamappid (string): The Steam App ID of the game.
            name (string): The name or keyword of the game server.
        """
        try:
            result = await self._search_server_ip(steamappid, name)
            return result

        except Exception as e:
            logger.error(f"调用 get_a2s_info 时出错: {e}")
            return f"⛔ 查询失败: {e}"
        
    @filter.llm_tool("get_ip_a2s_server_info")
    async def get_a2s_info(self, event: AstrMessageEvent, ip: str, port: str = "27015"):
        """Query A2S(A UDP-based game server query protocol) server information.

        Args:
            ip (string): The IP address of the server.
            port (string): The port number of the server, default is 27015.
        """
        try:
            result = await self._query_server(ip, port, render_as_image=False)
            return result

        except Exception as e:
            logger.error(f"调用 get_a2s_info 时出错: {e}")
            return f"⛔ 查询失败: {e}"
