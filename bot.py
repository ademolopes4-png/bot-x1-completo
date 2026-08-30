import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dicionários globais para gerenciar as filas de cada modo e tipo de gelo
# Estrutura: filas[modo][tipo_gelo] = [lista de membros]
filas = {
    "1v1": {"Gelo Normal": [], "Gelo Infinito": []},
    "2v2": {"Gelo Normal": [], "Gelo Infinito": []},
    "3v3": {"Gelo Normal": [], "Gelo Infinito": []}
}

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# --- VIEW DO PAINEL PRINCIPAL (COM RANKING NO TOPO E FILAS SEPARADAS) ---
class PainelCompletoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # Botões do 1v1
    @discord.ui.button(label="1v1 - Gelo Normal", style=discord.ButtonStyle.green, custom_id="1v1_normal", emoji="🧊", row=0)
    async def f_1v1_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "1v1", "Gelo Normal", 2)

    @discord.ui.button(label="1v1 - Gelo Infinito", style=discord.ButtonStyle.green, custom_id="1v1_infinito", emoji="🧊", row=0)
    async def f_1v1_infinito(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "1v1", "Gelo Infinito", 2)

    # Botões do 2v2
    @discord.ui.button(label="2v2 - Gelo Normal", style=discord.ButtonStyle.blurple, custom_id="2v2_normal", emoji="🧊", row=1)
    async def f_2v2_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "2v2", "Gelo Normal", 4)

    @discord.ui.button(label="2v2 - Gelo Infinito", style=discord.ButtonStyle.blurple, custom_id="2v2_infinito", emoji="🧊", row=1)
    async def f_2v2_infinito(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "2v2", "Gelo Infinito", 4)

    # Botões do 3v3
    @discord.ui.button(label="3v3 - Gelo Normal", style=discord.ButtonStyle.grey, custom_id="3v3_normal", emoji="🧊", row=2)
    async def f_3v3_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "3v3", "Gelo Normal", 6)

    @discord.ui.button(label="3v3 - Gelo Infinito", style=discord.ButtonStyle.grey, custom_id="3v3_infinito", emoji="🧊", row=2)
    async def f_3v3_infinito(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "3v3", "Gelo Infinito", 6)

    # Botão de Ranking
    @discord.ui.button(label="Ver Ranking Geral", style=discord.ButtonStyle.secondary, custom_id="btn_ranking", emoji="🏆", row=3)
    async def ver_ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🏆 **Ranking Geral:**\nNenhum jogador pontuou no ranking ainda.", ephemeral=True)

async def entrar_na_fila(interaction: discord.Interaction, modo: str, tipo_gelo: str, limite: int):
    user = interaction.user
    lista = filas[modo][tipo_gelo]

    if user in lista:
        await interaction.response.send_message("Você já está nessa fila!", ephemeral=True)
        return

    lista.append(user)
    
    if len(lista) < limite:
        # Mostra quem está esperando com o @
        nomes_esperando = ", ".join([m.mention for m in lista])
        await interaction.response.send_message(f"✅ Você entrou na fila **{modo} ({tipo_gelo})**!\n⏳ **Aguardando o oponente...** Jogadores na fila: {nomes_esperando}", ephemeral=True)
    else:
        # A fila encheu! Pega os jogadores necessários e limpa a fila
        jogadores_partida = lista[:limite]
        filas[modo][tipo_gelo] = [] # Limpa a fila

        await interaction.response.send_message(f"🚀 Fila completa para **{modo} ({tipo_gelo})**! Criando canal privado...", ephemeral=True)
        await criar_canal_partida(interaction.guild, modo, tipo_gelo, jogadores_partida)

async def criar_canal_partida(guild: discord.Guild, modo: str, tipo_gelo: str, jogadores: list):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    for jogador in jogadores:
        overwrites[jogador] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    # Cria a categoria ou canal de texto privado
    canal = await guild.create_text_channel(name=f"⚔️-{modo}-{tipo_gelo}".lower(), overwrites=overwrites)

    mencoes = ", ".join([j.mention for j in jogadores])
    
    view = ConfirmarPartidaView(jogadores, canal)
    embed = discord.Embed(
        title=f"Partida de {modo} | {tipo_gelo}",
        description=f"Jogadores: {mencoes}\n\n**Combinem suas regras e confirme a partida abaixo!**",
        color=0xff0000
    )
    await canal.send(content=mencoes, embed=embed, view=view)

# --- VIEW DE CONFIRMAÇÃO DE PARTIDA ---
class ConfirmarPartidaView(discord.ui.View):
    def __init__(self, jogadores, canal):
        super().__init__(timeout=None)
        self.jogadores = jogadores
        self.canal = canal
        self.confirmados = set()

    @discord.ui.button(label="Confirmar Partida", style=discord.ButtonStyle.green, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.jogadores:
            await interaction.response.send_message("Você não faz parte desta partida!", ephemeral=True)
            return

        self.confirmados.add(interaction.user)
        restantes = len(self.jogadores) - len(self.confirmados)

        if restantes > 0:
            await interaction.response.send_message(f"✅ {interaction.user.mention} confirmou! Faltam **{restantes}** confirmações.", ephemeral=False)
        else:
            await interaction.response.send_message("🎉 **Todas as confirmações realizadas!** Gerando sala...", ephemeral=False)
            
            # Desativa os botões de confirmação
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)

            # Manda o comando .cs para o bot de sala gerar
            await self.canal.send(".cs")

            # Envia o painel de definir vencedor logo após
            view_vencedor = DefinirVencedorView(self.jogadores, self.canal)
            await self.canal.send("🏆 **A partida foi iniciada!** Assim que terminar, defina o vencedor abaixo:", view=view_vencedor)

# --- VIEW DE DEFINIR VENCEDOR ---
class DefinirVencedorView(discord.ui.View):
    def __init__(self, jogadores, canal):
        super().__init__(timeout=None)
        self.jogadores = jogadores
        self.canal = canal

        # Adiciona dinamicamente um botão para cada jogador como vencedor
        for i, jogador in enumerate(jogadores):
            self.add_item(VencedorButton(jogador, label=f"Vencedor: {jogador.display_name}", row=i//2))

class VencedorButton(discord.ui.Button):
    def __init__(self, vencedor, label, row):
        super().__init__(style=discord.ButtonStyle.primary, label=label, row=row)
        self.vencedor = vencedor

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏆 **Vitória contabilizada para {self.vencedor.mention}!** Parabéns!\nEste canal será fechado em instantes.", ephemeral=False)
        
        # Aqui você pode adicionar lógica para salvar no ranking geral no futuro
        
        # Desativa os botões
        for child in self.view.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # Opcional: Deletar o canal após alguns segundos
        # await asyncio.sleep(10)
        # await interaction.channel.delete()

@bot.command(name="painel")
async def painel(ctx):
    # Ranking no topo e painel de filas logo abaixo
    embed = discord.Embed(
        title="🏆 PAINEL DE RANKING GERAL 🏆",
        description="1º 🥇 *Nenhum registrado*\n2º 🥈 *Nenhum registrado*\n3º 🥉 *Nenhum registrado*\n\n---------------------------------------------\n⚔️ **ESCOLHA SUA FILA ABAIXO:**",
        color=0xffd700
    )
    embed.set_thumbnail(url="https://i.imgur.com/4M34hi2.png") # Opcional
    
    view = PainelCompletoView()
    await ctx.send(embed=embed, view=view)

keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO: DISCORD_TOKEN não encontrado nas variáveis de ambiente!")

