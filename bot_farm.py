import io
import os
import re
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image
import pytesseract


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_shifts = {}


@bot.event
async def on_ready():
  await bot.tree.sync()
  print(f"Bot {bot.user} đã sẵn sàng với tính năng OCR!")


@bot.tree.command(
    name="batdau",
    description="Bắt đầu ca farm mới bằng cách tải lên ảnh chụp màn hình",
)
@app_commands.describe(
    image="Ảnh chụp màn hình chứa số Meso và Elixir ban đầu"
)
async def batdau(interaction: discord.Interaction, image: discord.Attachment):
  await interaction.response.defer(thinking=True)

  try:
    image_bytes = await image.read()
    pil_img = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(pil_img)

    numbers = re.findall(r"\d+", text.replace(",", ""))

    if len(numbers) >= 2:
      meso_val = int(numbers[0])
      elixir_val = int(numbers[1])

      active_shifts[interaction.user.id] = {
          "start_meso": meso_val,
          "start_elixir": elixir_val,
      }

      await interaction.followup.send(
          f"🟢 **ĐÃ BẮT ĐẦU CA THÀNH CÔNG!**\n"
          f"💰 Meso đầu: `{meso_val:,}`\n"
          f"🧪 Elixir đầu: `{elixir_val:,}`"
      )
    else:
      await interaction.followup.send(
          "⚠️ Không tìm thấy đủ thông số Meso và Elixir từ ảnh. Bạn hãy thử chụp"
          " lại rõ hơn nhé!"
      )
  except Exception as e:
    await interaction.followup.send(f"❌ Lỗi xử lý ảnh: `{str(e)}`")


@bot.tree.command(
    name="ketthuc",
    description="Kết thúc ca farm bằng cách tải lên ảnh chụp màn hình tổng kết",
)
@app_commands.describe(
    image="Ảnh chụp màn hình chứa số Meso và Elixir lúc kết thúc"
)
async def ketthuc(interaction: discord.Interaction, image: discord.Attachment):
  await interaction.response.defer(thinking=True)

  user_id = interaction.user.id
  if user_id not in active_shifts:
    await interaction.followup.send(
        "⚠️ Bạn chưa bắt đầu ca nào cả! Hãy dùng lệnh `/batdau` trước nhé."
    )
    return

  try:
    image_bytes = await image.read()
    pil_img = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(pil_img)

    numbers = re.findall(r"\d+", text.replace(",", ""))

    if len(numbers) >= 2:
      m_end = int(numbers[0])
      e_end = int(numbers[1])

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
      await interaction.followup.send(report)
    else:
      await interaction.followup.send(
          "⚠️ Không đọc được thông số từ ảnh tổng kết. Hãy chắc chắn ảnh chụp rõ"
          " số liệu!"
      )
  except Exception as e:
    await interaction.followup.send(f"❌ Lỗi xử lý ảnh: `{str(e)}`")


TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
  bot.run(TOKEN)
