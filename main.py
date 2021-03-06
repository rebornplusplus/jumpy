# Jumpy! - platform game
# Art from Kenney.nl
# Happy Tune by http://opengameart.org/users/syncopika
# Yippee by http://opengameart.org/users/snabisch

import pygame as pg
import random
import math
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

		# load images
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
		self.clouds = pg.sprite.Group()
		self.platforms = pg.sprite.Group()
		self.powerups = pg.sprite.Group()
		self.mobs = pg.sprite.Group()
		self.near_mobs = pg.sprite.Group()
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

		# check if mob is too close to player, add score
		for mob in self.mobs:
			if not self.near_mobs.has(mob):
				if self.rect_rect_dist(self.player.rect, mob.rect) < DIST_MOB_PLAYER:
					self.near_mobs.add(mob)

		# check if player hits a platform - only if falling
		if self.player.vel.y > 0:
			hits = pg.sprite.spritecollide(self.player, self.platforms, False)
			if hits:
				lowest = hits[0]
				found = False
				for hit in hits:
					if self.player.pos.x < hit.rect.right + 10 and \
					   self.player.pos.x > hit.rect.left - 10 and \
					   self.player.pos.y < hit.rect.centery:
						if not found or hit.rect.bottom > lowest.rect.bottom:
							lowest = hit
							found = True
				if found:
					self.player.pos.y = lowest.rect.top
					self.player.vel.y = 0
					self.player.jumping = False

		# if player reaches top 1/4 of screen, scroll
		if self.player.rect.top <= HEIGHT / 4:
			# spawn clouds
			if randrange(100) < CLOUD_SPAWN_PCT:
				Cloud(self)
			before_y = self.player.pos.y
			self.player.pos.y += max(abs(self.player.vel.y), 2)
			if self.playing:
				self.score += int((self.player.pos.y - before_y) * SCORE_DIST_MULTIPLIER)
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
					self.score += SCORE_PER_PLAT

		# power ups
		pow_hits = pg.sprite.spritecollide(self.player, self.powerups, True)
		for pow in pow_hits:
			if pow.type == 'boost':
				self.boost_sound.play()
				self.player.vel.y = min(0, self.player.vel.y) - BOOST_POWER
				self.player.jumping = False	# so jump_cut doesn't cut it

		# Die!
		if self.player.rect.bottom > HEIGHT:
			for sprite in self.all_sprites:
				sprite.rect.y -= max(self.player.vel.y, 7)
				if sprite.rect.bottom < 0:
					sprite.kill()
		if len(self.platforms) == 0:
			self.playing = False

		# # spawn new platforms
		# while self.playing and len(self.platforms) < AVG_PLATFORM_IN_SCREEN:
		# 	width = random.randrange(50, 100)
		# 	Platform(self, random.randrange(0, WIDTH - width), random.randrange(-75, -30))
		self.spawn_platforms()

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
				if event.key == pg.K_ESCAPE:
					pg.mixer.music.pause()
					self.wait_for_key()
					pg.mixer.music.unpause()
	
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
		self.draw_text("High Score: " + str(self.highscore), 22, WHITE, WIDTH / 2, 15)
		bunny_img = self.spritesheet.get_image(382, 763, 150, 181)
		bunny_img.set_colorkey(BLACK)
		bunny_rect = bunny_img.get_rect()
		bunny_rect.center = (WIDTH / 2, HEIGHT / 2)
		self.screen.blit(bunny_img, bunny_rect)
		self.draw_text("Arrows to move, Space to jump.", 22, WHITE, WIDTH / 2, bunny_rect.bottom + 40)
		self.draw_text("Press a key to continue.", 18, WHITE, WIDTH / 2, bunny_rect.bottom + 150)
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
		bunny_img = self.spritesheet.get_image(382, 946, 150, 174)
		bunny_img.set_colorkey(BLACK)
		bunny_rect = bunny_img.get_rect()
		bunny_rect.center = (WIDTH / 2, HEIGHT / 2)
		self.screen.blit(bunny_img, bunny_rect)
		self.draw_text("Score: " + str(self.score), 22, WHITE, WIDTH / 2, bunny_rect.bottom + 40)
		if self.score > self.highscore:
			self.highscore = self.score
			self.draw_text("NEW HIGH SCORE!", 22, WHITE, WIDTH / 2, bunny_rect.bottom + 85)
			self.write_data()
		else :
			self.draw_text("High Score: " + str(self.highscore), 22, WHITE, WIDTH / 2, bunny_rect.bottom + 85)
		self.draw_text("Press a key to play again.", 18, WHITE, WIDTH / 2, bunny_rect.bottom + 150)
		pg.display.flip()
		self.wait_for_key()
		pg.mixer.music.fadeout(500)

	def draw_text(self, text, size, color, x, y):
		font = pg.font.Font(self.font_name, size)
		text_surface = font.render(text, True, color)
		text_rect = text_surface.get_rect()
		text_rect.midtop = (x, y)
		self.screen.blit(text_surface, text_rect)
	
	def rect_rect_dist(self, rect1, rect2):
		x1, y1 = rect1.topleft
		x1b, y1b = rect1.bottomright
		x2, y2 = rect2.topleft
		x2b, y2b = rect2.bottomright
		left = x2b < x1
		right = x1b < x2
		top = y2b < y1
		bottom = y1b < y2
		if bottom and left:
			return math.hypot(x2b-x1, y2-y1b)
		elif left and top:
			return math.hypot(x2b-x1, y2b-y1)
		elif top and right:
			return math.hypot(x2-x1b, y2b-y1)
		elif right and bottom:
			return math.hypot(x2-x1b, y2-y1b)
		elif left:
			return x1 - x2b
		elif right:
			return x2 - x1b
		elif top:
			return y1 - y2b
		elif bottom:
			return y2 - y1b
		else:  # rectangles intersect
			return 0
	
	def spawn_platforms(self):
		# spawn new platforms so they don't overlap that much
		while self.player.rect.y < HEIGHT and len(self.platforms) < AVG_PLATFORM_IN_SCREEN:
			width = random.randrange(50, 100)
			cur = Platform(self, random.randrange(0, WIDTH - width), random.randrange(-75, -30))
			for plat in self.platforms:
				if cur is not plat and cur.rect.colliderect(plat):
					x1 = max(cur.rect.left, plat.rect.left)
					x2 = min(cur.rect.right, plat.rect.right)
					y1 = max(cur.rect.top, plat.rect.top)
					y2 = min(cur.rect.bottom, plat.rect.bottom)
					intersection = pg.Rect(x1, y1, x2 - x1, y2 - y1)
					if (intersection.width * intersection.height) / (cur.rect.width * cur.rect.height) > PLATFORM_OVERLAP_RATIO:
						cur.kill()
					if (intersection.width * intersection.height) / (plat.rect.width * plat.rect.height) > PLATFORM_OVERLAP_RATIO:
						plat.kill()

g = Game()
g.show_start_screen()
while g.running:
	g.new()
	g.show_go_screen()

pg.quit()
