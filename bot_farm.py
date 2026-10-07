import io
import os
import re
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image
import pytesseract
import requests

# Cấu hình intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Lưu trữ ca farm tạm thời của từng người
active_shifts = {}


class StartShiftModal(discord.ui.Modal, title="Bắt đầu ca farm"):
  meso_start = discord.ui.TextInput(
      label="Số Meso lúc đầu", placeholder="Ví dụ: 1000000", required=True
  )
  elixir_start = discord.ui.TextInput(
      label="Số bình Elixir lúc đầu", placeholder="Ví dụ: 200", required=True
  )

  async def on_submit(self, interaction: discord.Interaction):
    try:
      m = int(self.meso_start.value.replace(",", "").replace(".", ""))
      e = int(self.elixir_start.value.replace(",", ""))
      active_shifts[interaction.user.id] = {"start_meso": m, "start_elixir": e}
      await interaction.response.send_message(
          f"🚀 **ĐÃ BẮT ĐẦU CA!**\n💰 Meso đầu: `{m:,}` | 🧪 Elixir đầu:"
          f" `{e:,}`",
          ephemeral=True,
      )
    except ValueError:
      await interaction.response.send_message(
          "⚠️ Vui lòng chỉ nhập số hợp lệ!", ephemeral=True
      )


class EndShiftModal(discord.ui.Modal, title="Kết thúc ca farm"):
  meso_end = discord.ui.TextInput(
      label="Số Meso lúc sau", placeholder="Ví dụ: 2500000", required=True
  )
  elixir_end = discord.ui.TextInput(
      label="Số bình Elixir còn lại", placeholder="Ví dụ: 130", required=True
  )

  async def on_submit(self, interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in active_shifts:
      await interaction.response.send_message(
          "⚠️ Bạn chưa bấm bắt đầu ca!", ephemeral=True
      )
      return
    try:
      m_end = int(self.meso_end.value.replace(",", "").replace(".", ""))
      e_end = int(self.elixir_end.value.replace(",", ""))

      data = active_shifts[user_id]
      earned = m_end - data["start_meso"]
      used = data["start_elixir"] - e_end
      del active_shifts[user_id]

      report = (
          f"📊 **BÁO CÁO KẾT QUẢ CA FARM** - {interaction.user.mention}\n"
          f"----------------------------------------\n"
          f"💰 **Meso kiếm được:** `+{earned:,}`\n"
          f"🧪 **Elixir đã tiêu thụ:** `{used:,}` bình (Còn lại: `{e_end:,}`)\n"
          f"----------------------------------------"
      )
      await interaction.response.send_message(report)
    except ValueError:
      await interaction.response.send_message(
          "⚠️ Vui lòng chỉ nhập số hợp lệ!", ephemeral=True
      )


class FarmControlView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="🟢 Bắt đầu ca",
      style=discord.ButtonStyle.green,
      custom_id="btn_start",
  )
  async def start_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(StartShiftModal())

  @discord.ui.button(
      label="🔴 Kết thúc ca",
      style=discord.ButtonStyle.red,
      custom_id="btn_end",
  )
  async def end_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(EndShiftModal())


@bot.event
async def on_ready():
  await bot.tree.sync()
  print(f"Bot {bot.user} đã sẵn sàng hoạt động!")


@bot.tree.command(
    name="farm", description="Mở bảng điều khiển tính Meso & Elixir"
)
async def farm_panel(interaction: discord.Interaction):
  view = FarmControlView()
  await interaction.response.send_message(
      "🎮 **QUẢN LÝ MESO & ELIXIR MAPLE**\nBấm nút bên dưới để bắt đầu/kết thúc"
      " ca:",
      view=view,
  )


# Lấy Token từ biến môi trường trên Railway
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
  bot.run(TOKEN)
else:
  print("Lỗi: Không tìm thấy DISCORD_TOKEN trong biến môi trường!")
