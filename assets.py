import pygame

screen = pygame.display.set_mode((640, 360))

paddles = pygame.image.load("assets/paddles.png").convert()

blue_paddle = pygame.Surface((8, 32), pygame.SRCALPHA)
blue_paddle.blit(paddles, (0, 0), (0, 0, 8, 32))
blue_paddle.set_colorkey((0, 0, 0))

yellow_paddle = pygame.Surface((8, 24), pygame.SRCALPHA)
yellow_paddle.blit(paddles, (0, 0), (8, 0, 8, 32))
yellow_paddle.set_colorkey((0, 0, 0))

ball = pygame.image.load("assets/ball.png").convert()
ball.set_colorkey((0, 0, 0))
