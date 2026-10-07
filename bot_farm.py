import io
import os
import re
import discord
from discord.ext import commands
from PIL import Image
import pytesseract

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


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
    await interaction.response.send_message(
        "🟢 **Bắt đầu ca:** Vui lòng gửi/kéo thả ảnh chụp màn hình chứa Meso &"
        " Elixir vào khung chat trong vòng 60 giây tới nhé!",
        ephemeral=True,
    )

    def check(m):
      return (
          m.author == interaction.user
          and m.channel == interaction.channel
          and len(m.attachments) > 0
      )

    try:
      msg = await bot.wait_for("message", timeout=60.0, check=check)
      attachment = msg.attachments[0]

      image_bytes = await attachment.read()
      image = Image.open(io.BytesIO(image_bytes))
      text = pytesseract.image_to_string(image)

      numbers = re.findall(r"\d+", text.replace(",", ""))

      if len(numbers) >= 2:
        meso_val = int(numbers[0])
        elixir_val = int(numbers[1])
        await interaction.followup.send(
            f"✅ **Đọc thông số Bắt đầu ca thành công!**\n- Meso: `{meso_val:,}`\n-"
            f" Elixir: `{elixir_val:,}`"
        )
      else:
        await interaction.followup.send(
            "⚠️ Không nhận diện được đủ thông số từ ảnh. Bạn hãy thử chụp rõ hơn"
            " nhé!"
        )
    except Exception:
      await interaction.followup.send(
          "⏱️ Hết thời gian chờ gửi ảnh hoặc có lỗi xảy ra!", ephemeral=True
      )

  @discord.ui.button(
      label="🔴 Kết thúc ca",
      style=discord.ButtonStyle.red,
      custom_id="btn_end",
  )
  async def end_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_message(
        "🔴 **Kết thúc ca:** Vui lòng gửi/kéo thả ảnh chụp màn hình tổng kết vào"
        " khung chat trong vòng 60 giây tới nhé!",
        ephemeral=True,
    )

    def check(m):
      return (
          m.author == interaction.user
          and m.channel == interaction.channel
          and len(m.attachments) > 0
      )

    try:
      msg = await bot.wait_for("message", timeout=60.0, check=check)
      attachment = msg.attachments[0]

      image_bytes = await attachment.read()
      image = Image.open(io.BytesIO(image_bytes))
      text = pytesseract.image_to_string(image)

      numbers = re.findall(r"\d+", text.replace(",", ""))

      if len(numbers) >= 2:
        meso_val = int(numbers[0])
        elixir_val = int(numbers[1])
        await interaction.followup.send(
            f"✅ **Đọc thông số Kết thúc ca thành công!**\n- Meso:"
            f" `{meso_val:,}`\n- Elixir: `{elixir_val:,}`"
        )
      else:
        await interaction.followup.send(
            "⚠️ Không nhận diện được đủ thông số từ ảnh. Bạn hãy thử chụp rõ hơn"
            " nhé!"
        )
    except Exception:
      await interaction.followup.send(
          "⏱️ Hết thời gian chờ gửi ảnh hoặc có lỗi xảy ra!", ephemeral=True
      )


@bot.event
async def on_ready():
  await bot.tree.sync()
  print(f"Bot {bot.user} đã sẵn sàng!")


@bot.tree.command(name="farm", description="Mở bảng điều khiển quản lý ca farm")
async def farm(interaction: discord.Interaction):
  view = FarmControlView()
  await interaction.response.send_message(
      "🎮 **QUẢN LÝ MESO & ELIXIR MAPLE**\nBấm nút bên dưới để bắt đầu/kết thúc"
      " ca:",
      view=view,
  )


TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
  bot.run(TOKEN)
