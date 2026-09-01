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

# Estrutura das filas atualizada conforme solicitado
filas = {
    "1v1 - Gelo Normal": {"usuarios": [], "mensagem": None, "limite": 2},
    "1v1 - Gelo Infinito": {"usuarios": [], "mensagem": None, "limite": 2},
    "2v2": {"usuarios": [], "mensagem": None, "limite": 4},
    "3v3": {"usuarios": [], "mensagem": None, "limite": 6}
}

painel_mensagem_ref = None

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

class PainelCompletoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="1v1 Gelo Normal", style=discord.ButtonStyle.green, custom_id="1v1_normal", emoji="🧊", row=0)
    async def f_1v1_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await gerenciar_fila(interaction, "1v1 - Gelo Normal")

    @discord.ui.button(label="1v1 Gelo Infinito", style=discord.ButtonStyle.blurple, custom_id="1v1_infinito", emoji="❄️", row=0)
    async def f_1v1_infinito(self, interaction: discord.Interaction, button: discord.ui.Button):
        await gerenciar_fila(interaction, "1v1 - Gelo Infinito")

    @discord.ui.button(label="2v2", style=discord.ButtonStyle.grey, custom_id="2v2_normal", emoji="👥", row=1)
    async def f_2v2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await gerenciar_fila(interaction, "2v2")

    @discord.ui.button(label="3v3", style=discord.ButtonStyle.grey, custom_id="3v3_normal", emoji="🛡️", row=1)
    async def f_3v3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await gerenciar_fila(interaction, "3v3")

    @discord.ui.button(label="Ver Ranking Geral", style=discord.ButtonStyle.secondary, custom_id="btn_ranking", emoji="🏆", row=2)
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

async def gerenciar_fila(interaction: discord.Interaction, nome_fila: str):
    user = interaction.user
    dados_fila = filas[nome_fila]
    lista = dados_fila["usuarios"]

    # Verifica se o usuário já está em OUTRA fila ativa
    for f_nome, f_dados in filas.items():
        if user in f_dados["usuarios"]:
            if f_nome == nome_fila:
                await interaction.response.send_message("Você já está nesta fila!", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Você já está na fila **{f_nome}**. Saia dela antes de entrar em outra!", ephemeral=True)
            return

    lista.append(user)
    limite = dados_fila["limite"]
    
    if len(lista) < limite:
        await atualizar_embed_fila(interaction, nome_fila, primeira_vez=not dados_fila["mensagem"])
    else:
        jogadores_partida = lista[:limite]
        
        if dados_fila["mensagem"]:
            try:
                await dados_fila["mensagem"].delete()
            except:
                pass
            dados_fila["mensagem"] = None

        filas[nome_fila]["usuarios"] = []

        await interaction.response.send_message(f"🚀 **Fila completa para {nome_fila}!** Criando canal privado...", ephemeral=True)
        await criar_canal_partida(interaction.guild, nome_fila, jogadores_partida)

async def atualizar_embed_fila(interaction: discord.Interaction, nome_fila: str, primeira_vez=False):
    dados_fila = filas[nome_fila]
    lista = dados_fila["usuarios"]
    
    mencoes_fila = "\n".join([f"{m.mention}" for m in lista]) if lista else "*Nenhum jogador na fila*"
    
    embed = discord.Embed(
        title=f"⚔️ Fila: {nome_fila}",
        description=f"**Jogadores:**\n{mencoes_fila}\n\n⏳ *Aguardando o restante dos jogadores...*",
        color=0xff9900
    )
    embed.set_thumbnail(url="https://i.imgur.com/4M34hi2.png")
    
    view = FilaAcoesView(nome_fila)

    if primeira_vez:
        await interaction.response.send_message(embed=embed, view=view)
        dados_fila["mensagem"] = await interaction.original_response()
    else:
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except:
            if dados_fila["mensagem"]:
                await dados_fila["mensagem"].edit(embed=embed, view=view)

class FilaAcoesView(discord.ui.View):
    def __init__(self, nome_fila):
        super().__init__(timeout=None)
        self.nome_fila = nome_fila

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, emoji="➕", custom_id="btn_entrar")
    async def entrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await gerenciar_fila(interaction, self.nome_fila)

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.danger, emoji="✖️", custom_id="btn_sair")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        dados_fila = filas[self.nome_fila]
        lista = dados_fila["usuarios"]

        if user in lista:
            lista.remove(user)
            
            if len(lista) > 0:
                mencoes_fila = "\n".join([f"{m.mention}" for m in lista])
                embed = discord.Embed(
                    title=f"⚔️ Fila: {self.nome_fila}",
                    description=f"**Jogadores:**\n{mencoes_fila}\n\n⏳ *Aguardando o restante dos jogadores...*",
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

async def criar_canal_partida(guild: discord.Guild, nome_fila: str, jogadores: list):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_webhooks=True)
    }
    
    for jogador in jogadores:
        overwrites[jogador] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    canal = await guild.create_text_channel(name=f"⚔️-{nome_fila}".replace(" ", "-").replace("---", "-").lower(), overwrites=overwrites)

    mencoes = ", ".join([j.mention for j in jogadores])
    
    view = ConfirmarPartidaView(jogadores, canal)
    embed = discord.Embed(
        title=f"Partida de {nome_fila}",
        description=f"Jogadores: {mencoes}\n\n**Combinem suas regras e confirmem a partida abaixo!**",
        color=0xff0000
    )
    
    # Mensagem de saudação solicitada e menção aos jogadores
    await canal.send(content=f"Olá macaquitos 🦧 {mencoes}", embed=embed, view=view)

class ConfirmarPartidaView(discord.ui.View):
    def __init__(self, jogadores, canal):
        super().__init__(timeout=None)
        self.jogadores = jogadores
        self.canal = canal
        self.confirmados = set()

    @discord.ui.button(label="Confirmar Partida", style=discord.ButtonStyle.green, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.jogadores:
            await interaction.response.send_message("❌ Você não faz parte desta partida!", ephemeral=True)
            return

        self.confirmados.add(interaction.user)
        restantes = len(self.jogadores) - len(self.confirmados)

        if restantes > 0:
            await interaction.response.send_message(f"✅ {interaction.user.mention} confirmou! Faltam **{restantes}** confirmações.", ephemeral=False)
        else:
            await interaction.response.send_message("🎉 **Todas as confirmações realizadas!** Crie a sala manualmente.", ephemeral=False)
            
            for child in self.children:
                child.disabled = True
            try:
                await interaction.message.edit(view=self)
            except:
                pass

            view_vencedor = DefinirVencedorView(self.jogadores, self.canal)
            await self.canal.send("🏆 **A partida foi iniciada!** Assim que terminar, defina o vencedor ou feche a partida abaixo (Apenas Administradores):", view=view_vencedor)

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
        await ctx.send("⚠️ Uso correto: `!addvitorias @usuario quantidade`")

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
        await ctx.send("⚠️ Uso correto: `!removervitorias @usuario quantidade`")

@bot.command(name="removerfila")
@commands.has_permissions(administrator=True)
async def removerfila(ctx, membro: discord.Member):
    removido = False
    
    for modo, dados in filas.items():
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

