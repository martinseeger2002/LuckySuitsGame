import pygame
from threading import Timer
from decimal import Decimal
import pygame_gui
from pygame import mixer
import sys
import os
import configparser
import pygame.scrap
from bitcoinrpc.authproxy import AuthServiceProxy  # Import the AuthServiceProxy for RPC connection

# Import custom modules
from dealCard import deal_card  # Import the deal_card function
from getBalances import get_filtered_balances_and_utxos  # Import the get_filtered_balances_and_utxos function
from cashOut import send_lucky# Import the send_lucky function from cashOut.py
from buyIn import send_lucky

# Initialize Pygame and other modules
pygame.init()
mixer.init()

# Screen dimensions
WIDTH, HEIGHT = 1013, 760
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Suit and Color Betting Game")

# Global variables
player_address = None
rpc_config = None
rpc_connection = None
pool_address = "<Pool Address>"  # Pool address
credits = 0  # Initialize credits as an integer

# Colors and fonts
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
font = pygame.font.Font(None, 36)
shuffling_font = pygame.font.Font(None, 72)  # Larger font for the shuffling text

def get_base_path():
    """Get the base path for resource files."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def read_rpc_config():
    """Read RPC configuration from RPC.conf file."""
    base_path = get_base_path()
    config_path = os.path.join(base_path, 'RPC.conf')
    
    config = configparser.ConfigParser()
    try:
        with open(config_path, 'r') as config_file:
            config.read_file(config_file)
        
        if 'rpcconfig' not in config:
            raise ValueError("'rpcconfig' section not found in RPC.conf")
        
        rpc_config = {
            'rpcuser': config['rpcconfig'].get('rpcuser'),
            'rpcpassword': config['rpcconfig'].get('rpcpassword'),
            'rpchost': config['rpcconfig'].get('rpchost', 'localhost'),
            'rpcport': config['rpcconfig'].get('rpcport', '22555')
        }
        
        missing_fields = [key for key, value in rpc_config.items() if value is None]
        if missing_fields:
            raise ValueError(f"Missing required fields in RPC.conf: {', '.join(missing_fields)}")
        
        return rpc_config
    
    except FileNotFoundError:
        print(f"RPC.conf not found at {config_path}")
    except ValueError as e:
        print(f"Error in RPC.conf: {str(e)}")
    except Exception as e:
        print(f"Unexpected error reading RPC.conf: {str(e)}")
    
    return None

def load_image(filename):
    """Load an image from the data directory."""
    return pygame.image.load(os.path.join(get_base_path(), 'data', filename))

def load_resources():
    """Load images and sounds."""
    global background, suit_images, shuffling_sound
    background = load_image("pokerTable.webp")
    shuffling_sound = mixer.Sound(os.path.join(get_base_path(), 'data', "shuffling-cards-4.mp3"))
    # Load suit images and resize them
    suit_images = {
        "Hearts": load_image("Hearts.webp"),
        "Diamonds": load_image("Diamonds.webp"),
        "Clubs": load_image("Clubs.webp"),
        "Spades": load_image("Spades.webp")
    }
    for suit in suit_images:
        original_size = suit_images[suit].get_size()
        new_size = (int(original_size[0] * 0.6), int(original_size[1] * 0.6))
        suit_images[suit] = pygame.transform.scale(suit_images[suit], new_size)

def initialize_game():
    """Initialize the game state and RPC connection."""
    global rpc_config, rpc_connection
    rpc_config = read_rpc_config()
    if rpc_config:
        try:
            # Establish RPC connection using the credentials
            rpc_connection = AuthServiceProxy(f"http://{rpc_config['rpcuser']}:{rpc_config['rpcpassword']}@{rpc_config['rpchost']}:{rpc_config['rpcport']}")
        except Exception as e:
            print(f"Failed to connect to luckycoin RPC: {str(e)}")
            rpc_connection = None
    else:
        print("Failed to read RPC configuration.")
        rpc_connection = None
    load_resources()

def get_player_addresses_and_balances():
    """Retrieve a list of player addresses and their balances via RPC, excluding watch-only addresses."""
    global rpc_connection  # Use the global rpc_connection established in initialize_game

    # Retrieve the list of unspent outputs
    unspent_outputs = rpc_connection.listunspent()

    # Prepare a dictionary to aggregate balances by address
    address_balances = {}

    # Aggregate balances for each address
    for output in unspent_outputs:
        address = output['address']
        amount = output['amount']

        # Check if the address is watch-only
        address_info = rpc_connection.validateaddress(address)
        if address_info.get('iswatchonly', False):
            continue  # Skip watch-only addresses

        # Initialize the address balance if not already present
        if address not in address_balances:
            address_balances[address] = Decimal('0')

        # Add the amount to the address balance
        address_balances[address] += Decimal(amount)

    # Prepare the list of addresses and balances
    addresses_and_balances = []
    for address, balance in address_balances.items():
        # Only include addresses with a balance greater than 1.0
        if balance > 1.0:
            addresses_and_balances.append((address, balance))

    return addresses_and_balances

def player_address_ui():
    """Handle the player address selection screen."""
    global player_address, player_balance  # Ensure player_balance is global
    manager = pygame_gui.UIManager((WIDTH, HEIGHT))
    addresses = get_player_addresses_and_balances()
    if not addresses:
        # Handle error if no addresses are found
        print("No addresses found.")
        addresses = [('No Address', Decimal('0'))]
    
    # Prepare address options for the dropdown
    address_options = [(address, f"{address} ({balance} lucky)") for address, balance in addresses]
    
    dropdown = pygame_gui.elements.UIDropDownMenu(
        options_list=[option[1] for option in address_options],  # Use the formatted string for display
        starting_option=address_options[0][1] if address_options else "No Address",  # Use the formatted string for the starting option
        relative_rect=pygame.Rect((WIDTH//2 - 200, HEIGHT//2 - 20), (400, 40)),
        manager=manager
    )
    
    submit_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((WIDTH//2 - 50, HEIGHT//2 + 50), (100, 40)),
        text="Submit",
        manager=manager
    )
    
    running = True
    clock = pygame.time.Clock()
    while running:
        time_delta = clock.tick(60)/1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            manager.process_events(event)
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == submit_button:
                    selected_option = dropdown.selected_option
                    
                    # Debugging output to check the selected option
                    print(f"Selected Option: {selected_option}")

                    # Extract the display string from the selected option
                    selected_display = selected_option[0]  # Get the first element of the tuple

                    # Find the address corresponding to the selected display string
                    player_address = next((address for address, display in address_options if display == selected_display), None)
                    
                    # Debugging output to check the assigned player address
                    print(f"Selected Player Address: {player_address}")

                    if player_address is not None:
                        # Update player balance after selecting the address
                        player_balance = update_player_balance(player_address)  # Ensure player_balance is updated
                        print(f"Updated Player Balance: {player_balance}")
                    else:
                        print("No valid address selected.")
                    running = False  # Exit the UI
        manager.update(time_delta)
        # Draw background
        screen.blit(background, (0, 0))
        manager.draw_ui(screen)
        pygame.display.flip()

def update_player_balance(address):
    """Retrieve and return the balance for the given player address."""
    # Assuming you have a function to get the balance from the RPC
    balance = rpc_connection.getreceivedbyaddress(address)
    return balance

def suits_game_ui():
    """Handle the main game screen."""
    global credits, player_address  # Declare credits and player_address as global
    wager = 1
    result = ""
    selected_bet = None
    show_result = False
    result_timer = None
    deal_in_progress = False
    player_pool_balance = 0.0
    player_pool_utxos = []
    player_balance = Decimal('0')
    drawn_suit = None
    drawn_card = None
    buy_in_active = False
    buy_in_completed = False

    # Initialize cursors
    cursor_hand = pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND)
    cursor_arrow = pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW)
    pygame.mouse.set_cursor(cursor_hand)

    # Create buttons
    buttons, choice_buttons, other_buttons = create_game_buttons()

    # Update pool info
    player_pool_balance, player_pool_utxos, player_balance = update_pool_info()

    running = True
    clock = pygame.time.Clock()
    while running:
        time_delta = clock.tick(60)/1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Handle events
            credits, wager, result, selected_bet, deal_in_progress, player_pool_balance, player_balance = handle_game_events(
                event, buttons, choice_buttons, credits, wager, result, selected_bet, 
                deal_in_progress, player_pool_balance, player_balance
            )
            # Cursor change
            mouse_pos = pygame.mouse.get_pos()
            over_button = any(button.rect.collidepoint(mouse_pos) for button in buttons)
            pygame.mouse.set_cursor(cursor_hand if over_button else cursor_arrow)

        # Update game logic
        if deal_in_progress and not show_result:
            drawn_card, drawn_suit, credits, result, show_result, result_timer = process_deal(
                selected_bet, wager, credits, player_pool_balance
            )
            deal_in_progress = False

        # Draw screen
        # Draw background
        screen.blit(background, (0, 0))
        # Draw buttons
        for button in buttons:
            button.draw(screen)
        # Draw text displays
        draw_game_texts(screen, credits, wager, selected_bet, result, player_balance, player_pool_balance)
        if deal_in_progress and not show_result:
            shuffling_text_display = shuffling_font.render("Shuffling", True, WHITE)
            shuffling_rect = shuffling_text_display.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(shuffling_text_display, shuffling_rect)
        elif show_result:
            if drawn_suit and drawn_suit in suit_images:
                card_image = suit_images[drawn_suit]
                card_rect = card_image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
                screen.blit(card_image, card_rect)
            else:
                result_text_display = font.render("No card drawn", True, WHITE)
                result_rect = result_text_display.get_rect(center=(WIDTH // 2, HEIGHT // 2))
                screen.blit(result_text_display, result_rect)
            # Reset show_result after some time
            if result_timer and not result_timer.is_alive():
                show_result = False

        pygame.display.flip()

def handle_game_events(event, buttons, choice_buttons, credits, wager, result, selected_bet, deal_in_progress, player_pool_balance, player_balance):
    """Handle game events."""
    global rpc_connection, player_address
    if event.type == pygame.MOUSEBUTTONDOWN:
        pos = pygame.mouse.get_pos()
        for button in buttons:
            if button.is_clicked(pos):
                if button in choice_buttons:
                    selected_bet = button.text
                    result = f"You selected {selected_bet}"
                elif button.text == "Deal":
                    if not deal_in_progress and selected_bet and wager <= credits:
                        deal_in_progress = True
                        credits -= wager
                        shuffling_sound.play()
                    else:
                        result = "Cannot deal now."
                elif button.text == "- Bet":
                    if wager > 1:
                        wager -= 1
                elif button.text == "+ Bet":
                    if wager < calculate_max_wager(credits, player_pool_balance):
                        wager += 1
                elif button.text == "Buy In":
                    buy_in_amount = buy_in_ui()
                    if buy_in_amount is not None and buy_in_amount > 0:
                        success, new_credits, txid = handle_buy_in(buy_in_amount)
                        if success:
                            credits = new_credits  # Update credits only if the buy-in was successful
                            print(f"Buy-in successful. New credits: {credits}")
                            # Update player balance and pool balance
                            player_pool_balance, _, player_balance = update_pool_info()
                        else:
                            print("Buy-in failed, credits not updated.")
                elif button.text == "Cash Out":
                    if credits > 0:
                        txid = handle_cash_out(credits, player_address)
                        if txid:
                            result = f"Cashed out {credits} lucky. TXID: {txid}"
                            credits = 0
                            # Update player balance and pool balance
                            player_pool_balance, _, player_balance = update_pool_info()
                        else:
                            result = "Cash out failed. Please try again."
                    else:
                        result = "No credits to cash out."
                break
    return credits, wager, result, selected_bet, deal_in_progress, player_pool_balance, player_balance

def create_game_buttons():
    """Create buttons for the game."""
    # Calculate positions for centered suit buttons
    suit_width, suit_height = int(219 * 0.6), int(315 * 0.6)
    total_width = suit_width * 4
    spacing = 20  # Reduced spacing between buttons
    x_start = (WIDTH - total_width - spacing * 3) // 2
    y_start = (HEIGHT - suit_height - 50) // 2  # Centered vertically
    # Button dimensions
    button_width = 110
    button_height = 50
    # Create buttons
    buttons = [
        Button(x_start, y_start, suit_width, suit_height, "Hearts", RED, suit_images["Hearts"]),
        Button(x_start + suit_width + spacing, y_start, suit_width, suit_height, "Diamonds", RED, suit_images["Diamonds"]),
        Button(x_start + (suit_width + spacing) * 2, y_start, suit_width, suit_height, "Clubs", BLACK, suit_images["Clubs"]),
        Button(x_start + (suit_width + spacing) * 3, y_start, suit_width, suit_height, "Spades", BLACK, suit_images["Spades"]),
        Button(WIDTH // 2 - 110, y_start + suit_height + 20, button_width, button_height, "Red", RED),
        Button(WIDTH // 2 + 10, y_start + suit_height + 20, button_width, button_height, "Black", BLACK),
    ]
    choice_buttons = buttons.copy()  # These are the choice buttons
    buttons.extend([
        Button(WIDTH // 2 - button_width // 2, HEIGHT - button_height - 114, button_width, button_height, "Deal", GREEN),
        Button(WIDTH // 2 - button_width - 10, HEIGHT - button_height - 50, button_width, button_height, "- Bet", WHITE),
        Button(WIDTH // 2 + 10, HEIGHT - button_height - 50, button_width, button_height, "+ Bet", WHITE),
        Button(WIDTH - 240, 20, button_width, button_height, "Buy In", WHITE),
        Button(WIDTH - 120, 20, button_width, button_height, "Cash Out", WHITE)
    ])
    other_buttons = buttons[len(choice_buttons):]  # Non-choice buttons
    return buttons, choice_buttons, other_buttons

def calculate_max_wager(credits, player_pool_balance):
    """Calculate the maximum wager based on credits and pool balance."""
    pool_minus_credits = max(0, Decimal(player_pool_balance) - Decimal(credits))
    max_wager = min(credits, int(pool_minus_credits * Decimal('0.1')))
    return max(1, max_wager)  # Ensure minimum wager is 1

def process_deal(selected_bet, wager, credits, player_pool_balance):
    while True:
        drawn_card = deal_card()
        if not drawn_card.startswith("Jackpot"):
            break
    
    drawn_suit = drawn_card.split(" of ")[1]
    # Update pool info
    player_pool_balance, _, _ = update_pool_info()
    
    if selected_bet == drawn_suit:
        winnings = wager * 4  # 4x payout for correct suit
        credits += winnings
        result = f"You won {winnings}! Card: {drawn_card}."
    elif (selected_bet == "Red" and drawn_suit in ["Hearts", "Diamonds"]) or \
         (selected_bet == "Black" and drawn_suit in ["Clubs", "Spades"]):
        winnings = wager * 2  # 2x payout for correct color
        credits += winnings
        result = f"You won {winnings}! Card: {drawn_card}."
    else:
        result = f"You Won 0. Card: {drawn_card}"
    
    show_result = True
    result_timer = Timer(2.0, lambda: None)  # Placeholder
    result_timer.start()
    return drawn_card, drawn_suit, credits, result, show_result, result_timer

def update_pool_info():
    """Update player pool and balance information."""
    balances = get_filtered_balances_and_utxos(player_address, pool_address)
    player_pool_balance = balances['player_pool_wallet']['balance']
    player_pool_utxos = balances['player_pool_wallet']['utxos']
    player_balance = balances['player_wallet']['balance']
    return player_pool_balance, player_pool_utxos, player_balance

def draw_game_texts(screen, credits, wager, selected_bet, result, player_balance, player_pool_balance):
    """Draw the game texts on the screen."""
    credit_text = font.render(f"Credits: {credits}", True, WHITE)
    screen.blit(credit_text, (50, 50))
    max_wager = calculate_max_wager(credits, player_pool_balance)
    wager_text = font.render(f"Bet: {wager} of {max_wager} Max Bet", True, WHITE)
    screen.blit(wager_text, (50, 90))
    result_text_display = font.render(result, True, WHITE)
    screen.blit(result_text_display, (50, 130))
    if selected_bet:
        bet_text = font.render(f"Current Bet: {selected_bet}", True, WHITE)
        screen.blit(bet_text, (50, 170))
    
    # Ensure player_balance is a valid number
    if player_balance is None:
        player_balance = 0  # Default to 0 if player_balance is None
    player_balance_text = font.render(f"Player Balance: {int(player_balance)} lucky", True, WHITE)
    player_balance_rect = player_balance_text.get_rect(center=(WIDTH // 2, HEIGHT - 680))
    screen.blit(player_balance_text, player_balance_rect)
    player_pool_balance_text = font.render(f"Player Pool: {int(player_pool_balance)} lucky", True, WHITE)
    player_pool_balance_rect = player_pool_balance_text.get_rect(center=(WIDTH // 2, HEIGHT - 650))
    screen.blit(player_pool_balance_text, player_pool_balance_rect)


def handle_buy_in(buy_in_amount):
    """Handle the buy-in process and update credits."""
    global credits, player_address, pool_address, rpc_connection
    if buy_in_amount > 0:
        try:
            print(f"Attempting to buy in with amount: {buy_in_amount} to address: {pool_address}")
            
            # Call the send_lucky function from buyIn.py
            txid = send_lucky(player_address, pool_address, buy_in_amount)
            
            if txid:
                print(f"Buy-in successful. Transaction ID: {txid}")
                
                # Update pool info after buy-in
                player_pool_balance, _, player_balance = update_pool_info()
                
                # Increase credits by the buy-in amount
                new_credits = credits + buy_in_amount
                
                print(f"Updated Player Pool Balance: {player_pool_balance}")
                print(f"Updated Player Balance: {player_balance}")
                print(f"Credits increased by: {buy_in_amount}")
                
                return True, new_credits, txid
            else:
                print("Buy-in failed: No transaction ID returned from buyIn.py")
                return False, credits, None
        except Exception as e:
            print(f"Buy-in process failed: {str(e)}")
            import traceback
            traceback.print_exc()  # Print the full stack trace
            return False, credits, None
    else:
        print("Invalid buy-in amount.")
        return False, credits, None

def buy_in_ui():
    """Handle the buy-in screen and return the buy-in amount."""
    manager = pygame_gui.UIManager((WIDTH, HEIGHT))
    buy_in_amount = 0
    buy_in_text = pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect((WIDTH//2 - 100, HEIGHT//2 - 50), (200, 50)),
        text=f"Buy In Amount: {buy_in_amount}",
        manager=manager
    )
    button_width = 50
    button_height = 50
    spacing = 10
    total_width = button_width * 2 + spacing
    buy_in_minus = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((WIDTH//2 - total_width//2, HEIGHT//2 + 20), (button_width, button_height)),
        text="-",
        manager=manager
    )
    buy_in_plus = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((WIDTH//2 - total_width//2 + button_width + spacing, HEIGHT//2 + 20), (button_width, button_height)),
        text="+",
        manager=manager
    )
    buy_in_submit = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((WIDTH//2 - 60, HEIGHT//2 + 100), (120, 50)),
        text="Submit",
        manager=manager
    )
    running = True
    clock = pygame.time.Clock()
    while running:
        time_delta = clock.tick(60)/1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            manager.process_events(event)
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == buy_in_minus:
                    if buy_in_amount > 1:
                        buy_in_amount -= 1
                        buy_in_text.set_text(f"Buy In Amount: {buy_in_amount}")
                elif event.ui_element == buy_in_plus:
                    buy_in_amount += 1
                    buy_in_text.set_text(f"Buy In Amount: {buy_in_amount}")
                elif event.ui_element == buy_in_submit:
                    running = False
                    return buy_in_amount  # Return the buy-in amount
        manager.update(time_delta)
        # Draw background
        screen.blit(background, (0, 0))
        manager.draw_ui(screen)
        pygame.display.flip()
    
    return 0  # Return 0 if the UI is closed without submitting

class Button:
    """Custom Button class for handling game buttons."""
    def __init__(self, x, y, width, height, text, color, image=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.image = image
        self.is_pressed = False
    def draw(self, screen):
        if self.image:
            screen.blit(self.image, self.rect)
        else:
            pygame.draw.rect(screen, self.color, self.rect)
            text_color = BLACK if self.color != BLACK else WHITE
            text_surface = font.render(self.text, True, text_color)
            text_rect = text_surface.get_rect(center=self.rect.center)
            screen.blit(text_surface, text_rect)
        if self.is_pressed:
            pygame.draw.rect(screen, LIGHT_GRAY, self.rect, 3)
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

def handle_cash_out(amount, address):
    """Handle the cash out process."""
    from cashOut import send_lucky
    try:
        txid = send_lucky(address, amount)
        if txid:
            print(f"Cash out successful. TXID: {txid}")
            return txid
        else:
            print("Cash out failed: No transaction ID returned")
            return None
    except Exception as e:
        print(f"Cash out process failed: {str(e)}")
        import traceback
        traceback.print_exc()  # Print the full stack trace
        return None

def main():
    initialize_game()
    player_address_ui()
    suits_game_ui()

if __name__ == '__main__':
    main()