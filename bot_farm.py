import io
import os
import re
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageEnhance, ImageOps
import pytesseract

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_shifts = {}

def preprocess_and_ocr(pil_image):
    """
    Tiền xử lý ảnh mạnh mẽ để loại bỏ nhiễu nền game và nhận diện chữ số.
    """
    try:
        # 1. Chuyển sang ảnh xám (Grayscale)
        gray_image = ImageOps.grayscale(pil_image)

        # 2. Tăng độ tương phản lên mức tối đa
        enhancer = ImageEnhance.Contrast(gray_image)
        contrast_image = enhancer.enhance(5.0)

        # 3. Resize ảnh lên gấp đôi để Tesseract đọc dễ hơn (Upscaling)
        new_size = (contrast_image.size[0] * 2, contrast_image.size[1] * 2)
        large_image = contrast_image.resize(new_size, Image.Resampling.LANCZOS)

        # 4. Áp dụng ngưỡng nhị phân hóa (Binarization - chỉ giữ lại đen trắng)
        # Giá trị ngưỡng (threshold) có thể cần tinh chỉnh tùy ảnh, ở đây dùng 150
        threshold = 150
        binary_image = large_image.point(lambda p: 255 if p > threshold else 0)

        # Chạy OCR trên ảnh đã xử lý
        text = pytesseract.image_to_string(binary_image, config='--psm 6 digits') # config digits ép chỉ đọc số
        return text

    except Exception as e:
        print(f"❌ Lỗi tiền xử lý ảnh: {e}")
        return pytesseract.image_to_string(pil_image) # Trả về ảnh gốc nếu lỗi


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot {bot.user} đã sẵn sàng với chế độ OCR Tiền xử lý!")


@bot.tree.command(
    name="batdau",
    description="Bắt đầu ca farm (OCR Tiền xử lý)",
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

        # Cắt vùng chứa Meso (góc trên bên trái)
        crop_meso = pil_img.crop((0, 0, int(width * 0.45), int(height * 0.25)))
        text_meso = preprocess_and_ocr(crop_meso) # Dùng hàm tiền xử lý
        numbers_meso = re.findall(r"\d+", text_meso.replace(",", ""))

        # Cắt vùng chứa Elixir/Item (thanh Quick Slot)
        crop_elixir = pil_img.crop((int(width * 0.2), int(height * 0.55), int(width * 0.6), height))
        text_elixir = preprocess_and_ocr(crop_elixir) # Dùng hàm tiền xử lý
        numbers_elixir = re.findall(r"\d+", text_elixir.replace(",", ""))

        if numbers_meso and numbers_elixir:
            # Lọc ra các số có vẻ hợp lệ (ví dụ: > 3 chữ số cho Meso, > 0 cho Elixir)
            valid_meso = [int(n) for n in numbers_meso if len(n) > 4]
            valid_elixir = [int(n) for n in numbers_elixir if len(n) < 4]

            meso_val = max(valid_meso) if valid_meso else int(max(numbers_meso, key=len))
            elixir_val = min(valid_elixir) if valid_elixir else int(numbers_elixir[0])

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
                "⚠️ Không quét được thông số chính xác. Hãy chụp lại ảnh rõ nét, cắt đúng vùng"
                " như mẫu nhé!"
            )
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý ảnh: `{str(e)}`")


@bot.tree.command(
    name="ketthuc",
    description="Kết thúc ca farm (OCR Tiền xử lý)",
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

        crop_meso = pil_img.crop((0, 0, int(width * 0.45), int(height * 0.25)))
        text_meso = preprocess_and_ocr(crop_meso)
        numbers_meso = re.findall(r"\d+", text_meso.replace(",", ""))

        crop_elixir = pil_img.crop((int(width * 0.2), int(height * 0.55), int(width * 0.6), height))
        text_elixir = preprocess_and_ocr(crop_elixir)
        numbers_elixir = re.findall(r"\d+", text_elixir.replace(",", ""))

        if numbers_meso and numbers_elixir:
            valid_meso = [int(n) for n in numbers_meso if len(n) > 4]
            valid_elixir = [int(n) for n in numbers_elixir if len(n) < 4]

            m_end = max(valid_meso) if valid_meso else int(max(numbers_meso, key=len))
            e_end = min(valid_elixir) if valid_elixir else int(numbers_elixir[0])

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
                "⚠️ Không đọc được thông số từ ảnh tổng kết. Hãy thử lại!"
            )
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý ảnh: `{str(e)}`")


TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
