import os
import json
import asyncio
import discord
from discord.ext import commands
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

RANKING_FILE = "ranking.json"

def carregar_ranking():
    if os.path.exists(RANKING_FILE):
        try:
            with open(RANKING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_ranking(dados):
    with open(RANKING_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

def gerar_texto_ranking():
    ranking_data = carregar_ranking()
    if not ranking_data:
        return "1º 🥇 *Nenhum registrado*\n2º 🥈 *Nenhum registrado*\n3º 🥉 *Nenhum registrado*"
    
    ranking_ordenado = sorted(ranking_data.items(), key=lambda x: x[1]["vitorias"], reverse=True)
    medalhas = ["🥇", "🥈", "🥉", "4º", "5º", "6º", "7º", "8º", "9º", "10º"]
    linhas = []
    
    for i, (user_id, dados) in enumerate(ranking_ordenado[:10]):
        tag_medalha = medalhas[i] if i < len(medalhas) else f"{i+1}º"
        linhas.append(f"{tag_medalha} **{dados['nome']}** — 🏆 {dados['vitorias']} vitórias ({dados['pontos']} pts)")
    
    return "\n".join(linhas)

# Dicionários globais para gerenciar filas e painel
filas = {
    "1v1": {"Taxa R$ 0,30": {"usuarios": [], "mensagem": None}},
    "2v2": {"R$ 2,00": {"usuarios": [], "mensagem": None}, "R$ 4,00": {"usuarios": [], "mensagem": None}},
    "3v3": {"R$ 3,00": {"usuarios": [], "mensagem": None}, "R$ 6,00": {"usuarios": [], "mensagem": None}}
}

painel_mensagem_ref = None

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# --- VIEW DO PAINEL PRINCIPAL ---
class PainelCompletoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="1v1 - Taxa R$ 0,30", style=discord.ButtonStyle.green, custom_id="1v1_taxa", emoji="🪙", row=0)
    async def f_1v1_taxa(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "1v1", "Taxa R$ 0,30", 2)

    @discord.ui.button(label="2v2 - R$ 2,00", style=discord.ButtonStyle.blurple, custom_id="2v2_2rs", emoji="💵", row=1)
    async def f_2v2_2rs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "2v2", "R$ 2,00", 4)

    @discord.ui.button(label="2v2 - R$ 4,00", style=discord.ButtonStyle.blurple, custom_id="2v2_4rs", emoji="💵", row=1)
    async def f_2v2_4rs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "2v2", "R$ 4,00", 4)

    @discord.ui.button(label="3v3 - R$ 3,00", style=discord.ButtonStyle.grey, custom_id="3v3_3rs", emoji="💵", row=2)
    async def f_3v3_3rs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "3v3", "R$ 3,00", 6)

    @discord.ui.button(label="3v3 - R$ 6,00", style=discord.ButtonStyle.grey, custom_id="3v3_6rs", emoji="💵", row=2)
    async def f_3v3_6rs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "3v3", "R$ 6,00", 6)

    @discord.ui.button(label="Ver Ranking Geral", style=discord.ButtonStyle.secondary, custom_id="btn_ranking", emoji="🏆", row=3)
    async def ver_ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        texto_ranking = gerar_texto_ranking()
        embed = discord.Embed(
            title="🏆 TOP MELHORES JOGADORES 🏆",
            description=texto_ranking,
            color=0xffd700
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def atualizar_painel_global():
    global painel_mensagem_ref
    if painel_mensagem_ref:
        try:
            texto_ranking = gerar_texto_ranking()
            embed = discord.Embed(
                title="🏆 PAINEL DE RANKING GERAL 🏆",
                description=f"{texto_ranking}\n\n---------------------------------------------\n⚔️ **ESCOLHA SUA FILA ABAIXO:**",
                color=0xffd700
            )
            embed.set_thumbnail(url="https://i.imgur.com/4M34hi2.png")
            await painel_mensagem_ref.edit(embed=embed)
        except:
            pass

async def entrar_na_fila(interaction: discord.Interaction, modo: str, subcategoria: str, limite: int):
    user = interaction.user
    dados_fila = filas[modo][subcategoria]
    lista = dados_fila["usuarios"]

    if user in lista:
        await interaction.response.send_message("Você já está nessa fila!", ephemeral=True)
        return

    lista.append(user)
    
    if len(lista) < limite:
        mencoes_fila = "\n".join([f"{m.mention}" for m in lista])
        embed = discord.Embed(
            title=f"⚔️ Fila: {modo} | {subcategoria}",
            description=f"**Jogadores na fila:**\n{mencoes_fila}\n\n⏳ *Aguardando o restante dos jogadores...*",
            color=0xff9900
        )
        embed.set_thumbnail(url="https://i.imgur.com/4M34hi2.png")
        
        view = SairFilaView(modo, subcategoria)

        if dados_fila["mensagem"]:
            try:
                await dados_fila["mensagem"].edit(embed=embed, view=view)
                await interaction.response.defer()
            except:
                msg = await interaction.channel.send(embed=embed, view=view)
                dados_fila["mensagem"] = msg
                await interaction.response.defer()
        else:
            await interaction.response.send_message(embed=embed, view=view)
            dados_fila["mensagem"] = await interaction.original_response()
    else:
        jogadores_partida = lista[:limite]
        
        if dados_fila["mensagem"]:
            try:
                await dados_fila["mensagem"].delete()
            except:
                pass
            dados_fila["mensagem"] = None

        filas[modo][subcategoria]["usuarios"] = []

        await interaction.response.send_message(f"🚀 **Fila completa para {modo} ({subcategoria})!** Criando canal privado...", ephemeral=True)
        await criar_canal_partida(interaction.guild, modo, subcategoria, jogadores_partida)

# --- VIEW DO BOTÃO DE SAIR DA FILA ---
class SairFilaView(discord.ui.View):
    def __init__(self, modo, subcategoria):
        super().__init__(timeout=None)
        self.modo = modo
        self.subcategoria = subcategoria

    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.danger, emoji="✖️")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        dados_fila = filas[self.modo][self.subcategoria]
        lista = dados_fila["usuarios"]

        if user in lista:
            lista.remove(user)
            
            if len(lista) > 0:
                mencoes_fila = "\n".join([f"{m.mention}" for m in lista])
                embed = discord.Embed(
                    title=f"⚔️ Fila: {self.modo} | {self.subcategoria}",
                    description=f"**Jogadores na fila:**\n{mencoes_fila}\n\n⏳ *Aguardando o restante dos jogadores...*",
                    color=0xff9900
                )
                embed.set_thumbnail(url="https://i.imgur.com/4M34hi2.png")
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                if dados_fila["mensagem"]:
                    try:
                        await dados_fila["mensagem"].delete()
                    except:
                        pass
                    dados_fila["mensagem"] = None
                await interaction.response.defer()
        else:
            await interaction.response.send_message("Você não está nesta fila!", ephemeral=True)

async def criar_canal_partida(guild: discord.Guild, modo: str, subcategoria: str, jogadores: list):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    for jogador in jogadores:
        overwrites[jogador] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    canal = await guild.create_text_channel(name=f"⚔️-{modo}-{subcategoria}".replace("$", "").replace(",", "").replace(" ", "-").lower(), overwrites=overwrites)

    mencoes = ", ".join([j.mention for j in jogadores])
    
    view = ConfirmarPartidaView(jogadores, canal)
    embed = discord.Embed(
        title=f"Partida de {modo} | {subcategoria}",
        description=f"Jogadores: {mencoes}\n\n**Combinem suas regras, o valor da aposta e confirme a partida abaixo!**",
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
            
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)

            # Envia puramente o comando .cs isolado
            await self.canal.send(".cs")

            view_vencedor = DefinirVencedorView(self.jogadores, self.canal)
            await self.canal.send("🏆 **A partida foi iniciada!** Assim que terminar, defina o vencedor ou feche a partida abaixo (Apenas Administradores):", view=view_vencedor)

# --- VIEW DE DEFINIR VENCEDOR E FECHAR CANAL (APENAS ADMINS) ---
class DefinirVencedorView(discord.ui.View):
    def __init__(self, jogadores, canal):
        super().__init__(timeout=None)
        self.jogadores = jogadores
        self.canal = canal

        for i, jogador in enumerate(jogadores):
            self.add_item(VencedorButton(jogador, label=f"Vencedor: {jogador.display_name}", row=i//2))
        
        self.add_item(FecharCanalButton(row=2))

class VencedorButton(discord.ui.Button):
    def __init__(self, vencedor, label, row):
        super().__init__(style=discord.ButtonStyle.primary, label=label, row=row)
        self.vencedor = vencedor

    async def callback(self, interaction: discord.Interaction):
        # Validação de Administrador
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas **Administradores** podem definir o vencedor da partida!", ephemeral=True)
            return

        ranking_data = carregar_ranking()
        user_id_str = str(self.vencedor.id)
        
        if user_id_str not in ranking_data:
            ranking_data[user_id_str] = {"nome": self.vencedor.display_name, "vitorias": 0, "pontos": 0}
            
        ranking_data[user_id_str]["vitorias"] += 1
        ranking_data[user_id_str]["pontos"] += 10
        ranking_data[user_id_str]["nome"] = self.vencedor.display_name
        
        salvar_ranking(ranking_data)
        await atualizar_painel_global()

        await interaction.response.send_message(f"🏆 **Vitória contabilizada para {self.vencedor.mention}!** (+10 pontos)\n🔒 **Este canal será apagado automaticamente em 5 segundos...**", ephemeral=False)
        
        for child in self.view.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except:
            pass

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass

class FecharCanalButton(discord.ui.Button):
    def __init__(self, row):
        super().__init__(style=discord.ButtonStyle.danger, label="🔒 Fechar Canal", row=row, emoji="✖️")

    async def callback(self, interaction: discord.Interaction):
        # Validação de Administrador
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas **Administradores** podem fechar este canal!", ephemeral=True)
            return

        await interaction.response.send_message("🔒 **Canal encerrado manualmente pelo administrador! Apagando agora...**", ephemeral=False)
        
        for child in self.view.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except:
            pass

        await asyncio.sleep(2)
        try:
            await interaction.channel.delete()
        except:
            pass

# --- COMANDOS EXCLUSIVOS PARA ADMINISTRADORES ---

@bot.command(name="painel")
async def painel(ctx):
    global painel_mensagem_ref
    texto_ranking = gerar_texto_ranking()
    
    embed = discord.Embed(
        title="🏆 PAINEL DE RANKING GERAL 🏆",
        description=f"{texto_ranking}\n\n---------------------------------------------\n⚔️ **ESCOLHA SUA FILA ABAIXO:**",
        color=0xffd700
    )
    embed.set_thumbnail(url="https://i.imgur.com/4M34hi2.png")
    
    view = PainelCompletoView()
    painel_mensagem_ref = await ctx.send(embed=embed, view=view)

@bot.command(name="addvitorias")
@commands.has_permissions(administrator=True)
async def addvitorias(ctx, membro: discord.Member, quantidade: int):
    ranking_data = carregar_ranking()
    user_id_str = str(membro.id)

    if user_id_str not in ranking_data:
        ranking_data[user_id_str] = {"nome": membro.display_name, "vitorias": 0, "pontos": 0}

    ranking_data[user_id_str]["vitorias"] += quantidade
    ranking_data[user_id_str]["pontos"] += (quantidade * 10)
    ranking_data[user_id_str]["nome"] = membro.display_name

    salvar_ranking(ranking_data)
    await atualizar_painel_global()

    await ctx.send(f"✅ Adicionadas **{quantidade}** vitória(s) para {membro.mention} com sucesso!")

@addvitorias.error
async def addvitorias_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você precisa ser **Administrador** para usar este comando!")
    else:
        await ctx.send("⚠️ Uso correto: `!addvitorias @usuario quantidade` (Ex: `!addvitorias @fulano 2`)")

@bot.command(name="removervitorias")
@commands.has_permissions(administrator=True)
async def removervitorias(ctx, membro: discord.Member, quantidade: int):
    ranking_data = carregar_ranking()
    user_id_str = str(membro.id)

    if user_id_str not in ranking_data:
        await ctx.send(f"❌ O usuário {membro.mention} não possui registros no ranking.")
        return

    ranking_data[user_id_str]["vitorias"] = max(0, ranking_data[user_id_str]["vitorias"] - quantidade)
    ranking_data[user_id_str]["pontos"] = max(0, ranking_data[user_id_str]["pontos"] - (quantidade * 10))

    salvar_ranking(ranking_data)
    await atualizar_painel_global()

    await ctx.send(f"🗑️ Removidas **{quantidade}** vitória(s) de {membro.mention} com sucesso!")

@removervitorias.error
async def removervitorias_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você precisa ser **Administrador** para usar este comando!")
    else:
        await ctx.send("⚠️ Uso correto: `!removervitorias @usuario quantidade` (Ex: `!removervitorias @fulano 1`)")

@bot.command(name="removerfila")
@commands.has_permissions(administrator=True)
async def removerfila(ctx, membro: discord.Member):
    removido = False
    
    for modo, subcategorias in filas.items():
        for sub, dados in subcategorias.items():
            if membro in dados["usuarios"]:
                dados["usuarios"].remove(membro)
                removido = True
                
                if len(dados["usuarios"]) == 0 and dados["mensagem"]:
                    try:
                        await dados["mensagem"].delete()
                    except:
                        pass
                    dados["mensagem"] = None

    if removido:
        await ctx.send(f"🧹 O usuário {membro.mention} foi **removido de todas as filas** ativas por um administrador.")
    else:
        await ctx.send(f"⚠️ O usuário {membro.mention} não está em nenhuma fila no momento.")

@removerfila.error
async def removerfila_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você precisa ser **Administrador** para usar este comando!")
    else:
        await ctx.send("⚠️ Uso correto: `!removerfila @usuario`")

keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO: DISCORD_TOKEN não encontrado nas variáveis de ambiente!")

