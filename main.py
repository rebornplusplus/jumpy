# Jumpy! - platform game
# Art from Kenney.nl
# Happy Tune by http://opengameart.org/users/syncopika
# Yippee by http://opengameart.org/users/snabisch

import pygame as pg
import random
from settings import *
from sprites import *
from os import path

class Game:
	def __init__(self):
		# initialize game window, etc
		pg.init()
		pg.mixer.init()
		self.screen = pg.display.set_mode((WIDTH, HEIGHT))
		pg.display.set_caption(TITLE)
		self.clock = pg.time.Clock()
		self.running = True
		self.total_games = 0
		self.font_name = pg.font.match_font(FONT_NAME)
		self.load_data()

	def load_data(self):
		# load high score
		self.dir = path.dirname(__file__)
		try:
			with open(path.join(self.dir, HS_FILE), 'r') as f:
				self.highscore = int(f.read())
		except:
			self.highscore = 0

		# load spritesheet
		img_dir = path.join(self.dir, 'img')
		self.spritesheet = Spritesheet(path.join(img_dir, SPRITESHEET))
		self.cloud_images = []
		for i in range(1, 4):
			self.cloud_images.append(pg.image.load(path.join(img_dir, 'cloud{}.png'.format(i))).convert())

		# load sounds
		self.snd_dir = path.join(self.dir, 'snd')
		self.jump_sound = pg.mixer.Sound(path.join(self.snd_dir, 'Jump33.wav'))
		self.boost_sound = pg.mixer.Sound(path.join(self.snd_dir, 'Powerup31.wav'))

	def write_data(self):
		# write high score
		with open(path.join(self.dir, HS_FILE), 'w') as f:
			f.write(str(self.highscore))

	def new(self):
		# start a new game
		self.score = 0
		self.total_games += 1
		# sprite groups
		self.all_sprites = pg.sprite.LayeredUpdates()
		self.platforms = pg.sprite.Group()
		self.powerups = pg.sprite.Group()
		self.mobs = pg.sprite.Group()
		self.clouds = pg.sprite.Group()
		# create player
		self.player = Player(self)
		# spawn new clouds
		for i in range(CLOUD_CNT_INITIAL):
			c = Cloud(self)
			c.rect.y += CLOUD_SPAWN_OFFSET
		if self.total_games > 1:
			self.mob_time += MOB_SPAWN_INITIAL_TIME
		else:
			self.mob_time = MOB_SPAWN_INITIAL_TIME
		for plat in PLATFORM_LIST:
			Platform(self, *plat)
		# load music
		pg.mixer.music.load(path.join(self.snd_dir, 'Happy Tune.ogg'))
		# run game loop
		self.run()

	def run(self):
		# game loop
		pg.mixer.music.play(loops = -1)
		self.playing = True
		while self.playing:
			self.clock.tick(FPS)
			self.events()
			self.update()
			self.draw()
		pg.mixer.music.fadeout(500)

	def update(self):
		# game loop - update
		self.all_sprites.update()

		# spawn mob
		now = pg.time.get_ticks()
		if now - self.mob_time > MOB_FREQ + random.choice([-1000, -500, 0, 500, 1000]):
			self.mob_time = now
			Mob(self)

		# check if player hits a mob
		mob_hit = pg.sprite.spritecollide(self.player, self.mobs, False, pg.sprite.collide_mask)
		if mob_hit:
			for mob in mob_hit:
				if mob.rect.right < 0 or mob.rect.left > WIDTH:
					mob.kill()
				else:
					self.playing = False
					break

		# check if player hits a platform - only if falling
		if self.player.vel.y > 0:
			hits = pg.sprite.spritecollide(self.player, self.platforms, False)
			if hits:
				lowest = hits[0]
				for hit in hits:
					if hit.rect.bottom > lowest.rect.bottom:
						lowest = hit
				if self.player.pos.x < lowest.rect.right + 10 and \
				   self.player.pos.x > lowest.rect.left - 10:
					if self.player.pos.y < lowest.rect.centery:
						self.player.pos.y = lowest.rect.top
						self.player.vel.y = 0
						self.player.jumping = False

		# if player reaches top 1/4 of screen, scroll
		if self.player.rect.top <= HEIGHT / 4:
			# spawn clouds
			if randrange(100) < CLOUD_SPAWN_PCT:
				Cloud(self)
			self.player.pos.y += max(abs(self.player.vel.y), 2)
			for cloud in self.clouds:
				cloud.rect.y += max(abs(self.player.vel.y / 2), 2)
			for mob in self.mobs:
				mob.rect.y += max(abs(self.player.vel.y), 2)
				if mob.rect.top >= HEIGHT:
					mob.kill()
			for plat in self.platforms:
				plat.rect.y += max(abs(self.player.vel.y), 2)
				if plat.rect.top >= HEIGHT:
					plat.kill()
					self.score += 10

		# power ups
		pow_hits = pg.sprite.spritecollide(self.player, self.powerups, True)
		for pow in pow_hits:
			if pow.type == 'boost':
				self.boost_sound.play()
				self.player.vel.y = -BOOST_POWER
				self.player.jumping = False	# so jump_cut doesn't cut it

		# Die!
		if self.player.rect.bottom > HEIGHT:
			for sprite in self.all_sprites:
				sprite.rect.y -= max(self.player.vel.y, 7)
				if sprite.rect.bottom < 0:
					sprite.kill()
		if len(self.platforms) == 0:
			self.playing = False

		# spawn new platforms
		while self.playing and len(self.platforms) < AVG_PLATFORM_IN_SCREEN:
			width = random.randrange(50, 100)
			Platform(self, random.randrange(0, WIDTH - width), random.randrange(-75, -30))

	def events(self):
		# game loop - events
		for event in pg.event.get():
			# check for closing window
			if event.type == pg.QUIT:
				if self.playing:
					self.playing = False
				self.running = False

			if event.type == pg.KEYDOWN:
				if event.key == pg.K_SPACE or event.key == pg.K_w:
					self.player.jump()

			if event.type == pg.KEYUP:
				if event.key == pg.K_SPACE or event.key == pg.K_w:
					self.player.jump_cut()

	def draw(self):
		# game loop - draw
		self.screen.fill(BGCOLOR)
		self.all_sprites.draw(self.screen)
		self.draw_text(str(self.score), 22, WHITE, WIDTH / 2, 15)
		# *after* drawing everything, flip the display
		pg.display.flip()

	def wait_for_key(self):
		waiting = True
		while waiting:
			self.clock.tick(FPS)
			for event in pg.event.get():
				if event.type == pg.QUIT:
					waiting = False
					self.running = False
				if event.type == pg.KEYUP:
					waiting = False
			pg.display.flip()

	def show_start_screen(self):
		# game splash/start screen
		pg.mixer.music.load(path.join(self.snd_dir, 'Yippee.ogg'))
		pg.mixer.music.play(loops = -1)
		self.screen.fill(BGCOLOR)
		self.draw_text(TITLE, 50, WHITE, WIDTH / 2, HEIGHT / 4)
		self.draw_text("Arrows to move, Space to jump.", 22, WHITE, WIDTH / 2, HEIGHT / 2)
		self.draw_text("Press a key to continue...", 18, WHITE, WIDTH / 2, HEIGHT * 3 / 4)
		self.draw_text("High Score: " + str(self.highscore), 22, WHITE, WIDTH / 2, 15)
		pg.display.flip()
		self.wait_for_key()
		pg.mixer.music.fadeout(500)

	def show_go_screen(self):
		# game over/continue
		if not self.running:
			return

		pg.mixer.music.load(path.join(self.snd_dir, 'Yippee.ogg'))
		pg.mixer.music.play(loops = -1)

		self.screen.fill(BGCOLOR)
		self.draw_text("Game Over!", 50, WHITE, WIDTH / 2, HEIGHT / 4)
		self.draw_text("Score: " + str(self.score), 22, WHITE, WIDTH / 2, HEIGHT / 2)
		self.draw_text("Press a key to play again.", 18, WHITE, WIDTH / 2, HEIGHT * 3 / 4)
		if self.score > self.highscore:
			self.highscore = self.score
			self.draw_text("NEW HIGH SCORE!", 22, WHITE, WIDTH / 2, HEIGHT / 2 + 40)
			self.write_data()
		else :
			self.draw_text("High Score: " + str(self.highscore), 22, WHITE, WIDTH / 2, HEIGHT / 2 + 40)
		pg.display.flip()
		self.wait_for_key()
		pg.mixer.music.fadeout(500)


	def draw_text(self, text, size, color, x, y):
		font = pg.font.Font(self.font_name, size)
		text_surface = font.render(text, True, color)
		text_rect = text_surface.get_rect()
		text_rect.midtop = (x, y)
		self.screen.blit(text_surface, text_rect)

g = Game()
g.show_start_screen()
while g.running:
	g.new()
	g.show_go_screen()

pg.quit()
