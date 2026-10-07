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
  print(f"Bot {bot.user} đã sẵn sàng với tính năng OCR chuẩn xác!")


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
    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = pil_img.size

    # 1. Cắt vùng chứa Meso (góc trên bên trái: x từ 0 đến 40%, y từ 0 đến 25%)
    crop_meso = pil_img.crop((0, 0, int(width * 0.4), int(height * 0.25)))
    text_meso = pytesseract.image_to_string(crop_meso)
    numbers_meso = re.findall(r"\d+", text_meso.replace(",", ""))

    # 2. Cắt vùng chứa Elixir/Item (khu vực thanh Quick Slot bên dưới: x từ 20% đến 55%, y từ 60% đến 100%)
    crop_elixir = pil_img.crop(
        (int(width * 0.2), int(height * 0.6), int(width * 0.55), height)
    )
    text_elixir = pytesseract.image_to_string(crop_elixir)
    numbers_elixir = re.findall(r"\d+", text_elixir.replace(",", ""))

    if numbers_meso and numbers_elixir:
      # Lấy số lớn nhất hoặc con số hợp lý làm Meso, lấy số lượng bình làm Elixir
      meso_val = int(
          max(numbers_meso, key=len)
      )  # Meso thường là số nhiều chữ số nhất
      elixir_val = int(numbers_elixir[0])  # Lấy con số đầu tiên tìm thấy ở quickslot

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
          "⚠️ Không quét được đủ thông số Meso và Elixir. Hãy chắc chắn ảnh chụp"
          " giữ nguyên khung hình như mẫu nhé!"
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
    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = pil_img.size

    # Cắt tương tự cho ảnh kết thúc
    crop_meso = pil_img.crop((0, 0, int(width * 0.4), int(height * 0.25)))
    text_meso = pytesseract.image_to_string(crop_meso)
    numbers_meso = re.findall(r"\d+", text_meso.replace(",", ""))

    crop_elixir = pil_img.crop(
        (int(width * 0.2), int(height * 0.6), int(width * 0.55), height)
    )
    text_elixir = pytesseract.image_to_string(crop_elixir)
    numbers_elixir = re.findall(r"\d+", text_elixir.replace(",", ""))

    if numbers_meso and numbers_elixir:
      m_end = int(max(numbers_meso, key=len))
      e_end = int(numbers_elixir[0])

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
          "⚠️ Không đọc được thông số từ ảnh tổng kết. Hãy thử chụp lại rõ hơn!"
      )
  except Exception as e:
    await interaction.followup.send(f"❌ Lỗi xử lý ảnh: `{str(e)}`")


TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
  bot.run(TOKEN)
