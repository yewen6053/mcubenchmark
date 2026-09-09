/*
 * mcu_stub.h - seeded common type/function declarations for cross-compiling
 * generated MCU/edge firmware C code with arm-none-eabi-gcc.
 *
 * Purpose: provide the most common vendor-SDK symbols so the generated code
 * compiles as *valid C for an ARM Cortex-M target*. This isolates GENUINE C
 * defects (type mismatches, wrong args to user logic, constraint violations,
 * missing semicolons) from ordinary "needs the vendor SDK" references.
 *
 * The evaluator's auto-stub loop recovers from any symbol we did not seed.
 * This header intentionally does NOT declare generic functions that models
 * frequently define themselves (gpio_init, adc_init, uart_init, ...) to avoid
 * redeclaration conflicts -- those are handled by the auto-stub loop instead.
 */
#ifndef MCU_STUB_H
#define MCU_STUB_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifndef NULL
#define NULL ((void*)0)
#endif

/* ---------------- STM32 HAL (most common framework) ---------------- */
typedef enum { HAL_OK = 0, HAL_ERROR = 1, HAL_BUSY = 2, HAL_TIMEOUT = 3 } HAL_StatusTypeDef;
typedef enum { RESET = 0, SET = 1 } FlagStatus, ITStatus;
typedef enum { DISABLE = 0, ENABLE = 1 } FunctionalState;
typedef enum { HAL_UNLOCKED = 0, HAL_LOCKED = 1 } HAL_LockTypeDef;

typedef struct {
    volatile uint32_t MODER, OTYPER, OSPEEDR, PUPDR, IDR, ODR, BSRR, LCKR, AFR[2];
} GPIO_TypeDef;

typedef struct {
    uint32_t Pin;
    uint32_t Mode;
    uint32_t Pull;
    uint32_t Speed;
    uint32_t Alternate;
} GPIO_InitTypeDef;

typedef struct {
    volatile uint32_t SR, DR, BRR, CR1, CR2, CR3, GTPR;
} USART_TypeDef;

/* NOTE (round08): the `Init` member of every HAL handle used to be `void *`.
 * That made perfectly correct STM32Cube code -
 *     huart1.Init.BaudRate = 115200;
 * - fail with "request for member 'BaudRate' in something not a structure or
 * union", i.e. a missing-SDK gap was reported as a *genuine* C defect. The
 * Init structs below mirror the real STM32Cube HAL field names so that only
 * true defects are counted. Field types are simplified to uint32_t; the
 * evaluation only needs the names to resolve, not the exact bit layout. */
typedef struct {
    uint32_t BaudRate, WordLength, StopBits, Parity, Mode, HwFlowCtl,
             OverSampling, OneBitSampling, ClockPrescaler;
} UART_InitTypeDef;

typedef struct {
    USART_TypeDef *Instance;
    UART_InitTypeDef Init;
    uint8_t *pTxBuffPtr;
    uint16_t TxXferSize, TxXferCount;
    uint8_t *pRxBuffPtr;
    uint16_t RxXferSize, RxXferCount;
    void *hdmatx, *hdmarx;
    void *Lock;
    volatile uint32_t State;
    volatile uint32_t gState, RxState;
    volatile uint32_t ErrorCode;
} UART_HandleTypeDef;

typedef struct {
    uint32_t ClockSpeed, DutyCycle, OwnAddress1, AddressingMode,
             DualAddressMode, OwnAddress2, GeneralCallMode, NoStretchMode,
             Timing;
} I2C_InitTypeDef;

typedef struct {
    void *Instance;
    I2C_InitTypeDef Init;
    uint8_t *pBuffPtr;
    uint16_t XferSize, XferCount;
    void *hdmatx, *hdmarx;
    void *Lock;
    volatile uint32_t State, PreviousState, Mode;
    volatile uint32_t ErrorCode;
} I2C_HandleTypeDef;

typedef struct {
    uint32_t Mode, Direction, DataSize, CLKPolarity, CLKPhase, NSS,
             BaudRatePrescaler, FirstBit, TIMode, CRCCalculation, CRCPolynomial,
             NSSPMode;
} SPI_InitTypeDef;

typedef struct {
    void *Instance;
    SPI_InitTypeDef Init;
    uint8_t *pTxBuffPtr, *pRxBuffPtr;
    uint16_t TxXferSize, TxXferCount, RxXferSize, RxXferCount;
    void *hdmatx, *hdmarx;
    void *Lock;
    volatile uint32_t State;
    volatile uint32_t ErrorCode;
} SPI_HandleTypeDef;

typedef struct {
    uint32_t ClockPrescaler, Resolution, DataAlign, ScanConvMode,
             EOCSelection, ContinuousConvMode, NbrOfConversion,
             DiscontinuousConvMode, NbrOfDiscConversion, ExternalTrigConv,
             ExternalTrigConvEdge, DMAContinuousRequests, LowPowerAutoWait,
             Overrun, SamplingTimeCommon;
} ADC_InitTypeDef;

typedef struct {
    void *Instance;
    ADC_InitTypeDef Init;
    void *DMA_Handle;
    void *Lock;
    volatile uint32_t State;
    volatile uint32_t ErrorCode;
} ADC_HandleTypeDef;

typedef struct {
    uint32_t Prescaler, CounterMode, Period, ClockDivision,
             RepetitionCounter, AutoReloadPreload;
} TIM_Base_InitTypeDef;

typedef struct {
    void *Instance;
    TIM_Base_InitTypeDef Init;
    uint32_t Channel;
    void *hdma[7];
    void *Lock;
    volatile uint32_t State;
} TIM_HandleTypeDef;

typedef struct {
    uint32_t Channel, Direction, PeriphInc, MemInc, PeriphDataAlignment,
             MemDataAlignment, Mode, Priority, FIFOMode, FIFOThreshold,
             MemBurst, PeriphBurst, Request;
} DMA_InitTypeDef;

typedef struct {
    void *Instance;
    DMA_InitTypeDef Init;
    void *Lock;
    volatile uint32_t State;
    void *Parent;
    void (*XferCpltCallback)(void *);
    void (*XferHalfCpltCallback)(void *);
    void (*XferErrorCallback)(void *);
    volatile uint32_t ErrorCode;
} DMA_HandleTypeDef;

typedef struct {
    uint32_t Channel, Rank, SamplingTime, SingleDiff, OffsetNumber, Offset;
} ADC_ChannelConfTypeDef;
typedef struct {
    uint32_t OCMode, Pulse, OCPolarity, OCNPolarity, OCFastMode,
             OCIdleState, OCNIdleState;
} TIM_OC_InitTypeDef;
typedef struct {
    uint32_t ClockSource, ClockPolarity, ClockPrescaler, ClockFilter;
} TIM_ClockConfigTypeDef;
typedef struct {
    uint32_t MasterOutputTrigger, MasterSlaveMode;
} TIM_MasterConfigTypeDef;
typedef struct {
    uint32_t ICPolarity, ICSelection, ICPrescaler, ICFilter;
} TIM_IC_InitTypeDef;
typedef struct {
    uint32_t OscillatorType, HSEState, HSEPredivValue, LSEState, HSIState,
             HSICalibrationValue, LSIState, MSIState, MSICalibrationValue,
             MSIClockRange;
    struct { uint32_t PLLState, PLLSource, PLLM, PLLN, PLLP, PLLQ, PLLR,
                      PLLMUL, PREDIV; } PLL;
} RCC_OscInitTypeDef;
typedef struct {
    uint32_t ClockType, SYSCLKSource, AHBCLKDivider, APB1CLKDivider,
             APB2CLKDivider;
} RCC_ClkInitTypeDef;
typedef struct {
    uint32_t PeriphClockSelection, AdcClockSelection, RTCClockSelection,
             Usart1ClockSelection, I2c1ClockSelection;
} RCC_PeriphCLKInitTypeDef;
HAL_StatusTypeDef HAL_RCC_OscConfig(RCC_OscInitTypeDef *osc);
HAL_StatusTypeDef HAL_RCC_ClockConfig(RCC_ClkInitTypeDef *clk, uint32_t flash_latency);
HAL_StatusTypeDef HAL_RCCEx_PeriphCLKConfig(RCC_PeriphCLKInitTypeDef *p);
HAL_StatusTypeDef HAL_TIM_ConfigClockSource(TIM_HandleTypeDef *htim, TIM_ClockConfigTypeDef *c);
HAL_StatusTypeDef HAL_TIMEx_MasterConfigSynchronization(TIM_HandleTypeDef *htim, TIM_MasterConfigTypeDef *m);
HAL_StatusTypeDef HAL_TIM_IC_ConfigChannel(TIM_HandleTypeDef *htim, TIM_IC_InitTypeDef *ic, uint32_t ch);
HAL_StatusTypeDef HAL_ADCEx_Calibration_Start(ADC_HandleTypeDef *hadc);
uint32_t HAL_RCC_GetPCLK1Freq(void);
uint32_t HAL_RCC_GetPCLK2Freq(void);
uint32_t HAL_RCC_GetHCLKFreq(void);
uint32_t HAL_RCC_GetSysClockFreq(void);

typedef enum { NVIC_ST_IRQRX = 0 } IRQn_Type;

/* Common STM32 macros */
#define GPIO_PIN_0 ((uint16_t)0x0001)
#define GPIO_PIN_1 ((uint16_t)0x0002)
#define GPIO_PIN_2 ((uint16_t)0x0004)
#define GPIO_PIN_3 ((uint16_t)0x0008)
#define GPIO_PIN_4 ((uint16_t)0x0010)
#define GPIO_PIN_5 ((uint16_t)0x0020)
#define GPIO_PIN_6 ((uint16_t)0x0040)
#define GPIO_PIN_7 ((uint16_t)0x0080)
#define GPIO_PIN_8 ((uint16_t)0x0100)
#define GPIO_PIN_9 ((uint16_t)0x0200)
#define GPIO_PIN_10 ((uint16_t)0x0400)
#define GPIO_PIN_11 ((uint16_t)0x0800)
#define GPIO_PIN_12 ((uint16_t)0x1000)
#define GPIO_PIN_13 ((uint16_t)0x2000)
#define GPIO_PIN_14 ((uint16_t)0x4000)
#define GPIO_PIN_15 ((uint16_t)0x8000)
#define GPIO_PIN_All ((uint16_t)0xFFFF)

#define GPIO_MODE_INPUT 0x00000000u
#define GPIO_MODE_OUTPUT_PP 0x00000001u
#define GPIO_MODE_OUTPUT_OD 0x00000011u
#define GPIO_MODE_AF_PP 0x00000002u
#define GPIO_MODE_AF_OD 0x00000012u
#define GPIO_MODE_ANALOG 0x00000003u
#define GPIO_MODE_IT_RISING 0x10110000u
#define GPIO_MODE_IT_FALLING 0x10210000u
#define GPIO_MODE_IT_RISING_FALLING 0x10310000u

#define GPIO_NOPULL 0x00000000u
#define GPIO_PULLUP 0x00000001u
#define GPIO_PULLDOWN 0x00000002u

#define GPIO_SPEED_FREQ_LOW 0x00000000u
#define GPIO_SPEED_FREQ_MEDIUM 0x00000001u
#define GPIO_SPEED_FREQ_HIGH 0x00000002u
#define GPIO_SPEED_FREQ_VERY_HIGH 0x00000003u

#define GPIO_PIN_RESET 0
#define GPIO_PIN_SET 1

/* Common STM32 peripheral base identifiers.
   Declared as `const` pointer VARIABLES (not macros) so that a model's own
   `#define LED_PORT GPIOB` style aliases cannot trigger preprocessor
   macro-redefinition / expansion errors during stub compilation.
   The numeric address is illustrative; only the typed pointer matters for
   cross-compilation type-checking. */
GPIO_TypeDef *const GPIOA = (GPIO_TypeDef*)0x40010800U;
GPIO_TypeDef *const GPIOB = (GPIO_TypeDef*)0x40010C00U;
GPIO_TypeDef *const GPIOC = (GPIO_TypeDef*)0x40011000U;
GPIO_TypeDef *const GPIOD = (GPIO_TypeDef*)0x40011400U;
GPIO_TypeDef *const GPIOE = (GPIO_TypeDef*)0x40011800U;
GPIO_TypeDef *const GPIOF = (GPIO_TypeDef*)0x40011C00U;
GPIO_TypeDef *const GPIOG = (GPIO_TypeDef*)0x40012000U;
GPIO_TypeDef *const GPIOH = (GPIO_TypeDef*)0x40012400U;
GPIO_TypeDef *const GPIOI = (GPIO_TypeDef*)0x40012800U;
USART_TypeDef *const USART1 = (USART_TypeDef*)0x40013800U;
USART_TypeDef *const USART2 = (USART_TypeDef*)0x40004400U;
USART_TypeDef *const USART3 = (USART_TypeDef*)0x40004800U;
void *const RCC   = (void*)0x40021000U;
void *const PWR   = (void*)0x40007000U;
void *const FLASH = (void*)0x40022000U;
void *const EXTI  = (void*)0x40010400U;
void *const SPI1   = (void*)0x40013000U;
void *const SPI2   = (void*)0x40003800U;
void *const I2C1   = (void*)0x40005400U;
void *const I2C2   = (void*)0x40005800U;
void *const TIM1   = (void*)0x40012C00U;
void *const TIM2   = (void*)0x40000000U;
void *const TIM3   = (void*)0x40000400U;
void *const TIM4   = (void*)0x40000800U;
void *const ADC1   = (void*)0x40012400U;
void *const DMA1   = (void*)0x40020000U;

#define ADC_CHANNEL_0 0
#define ADC_CHANNEL_1 1
#define ADC_SOFTWARE_START 0
#define TIM_CHANNEL_1 0
#define TIM_CHANNEL_2 1
#define UART_MODE_TX_RX 0
#define I2C_ADDRESSINGMODE_7BIT 0

/* Common STM32 HAL functions (models call, never define) */
HAL_StatusTypeDef HAL_Init(void);
HAL_StatusTypeDef HAL_DeInit(void);
void HAL_IncTick(void);
void HAL_Delay(uint32_t Delay);
uint32_t HAL_GetTick(void);
void HAL_GPIO_Init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *GPIO_InitStruct);
void HAL_GPIO_WritePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin, uint8_t PinState);
uint8_t HAL_GPIO_ReadPin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin);
void HAL_GPIO_TogglePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin);
HAL_StatusTypeDef HAL_UART_Init(UART_HandleTypeDef *huart);
HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_UART_Receive(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_I2C_Init(I2C_HandleTypeDef *hi2c);
HAL_StatusTypeDef HAL_I2C_Mem_Write(I2C_HandleTypeDef *hi2c, uint16_t DevAddress, uint16_t MemAddress, uint16_t MemAddSize, uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_I2C_Mem_Read(I2C_HandleTypeDef *hi2c, uint16_t DevAddress, uint16_t MemAddress, uint16_t MemAddSize, uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_I2C_Master_Transmit(I2C_HandleTypeDef *hi2c, uint16_t DevAddress, uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_I2C_Master_Receive(I2C_HandleTypeDef *hi2c, uint16_t DevAddress, uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_SPI_Init(SPI_HandleTypeDef *hspi);
HAL_StatusTypeDef HAL_SPI_Transmit(SPI_HandleTypeDef *hspi, uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_SPI_Receive(SPI_HandleTypeDef *hspi, uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_TIM_Base_Init(TIM_HandleTypeDef *htim);
HAL_StatusTypeDef HAL_TIM_Base_Start(TIM_HandleTypeDef *htim);
HAL_StatusTypeDef HAL_TIM_Base_Stop(TIM_HandleTypeDef *htim);
HAL_StatusTypeDef HAL_TIM_OC_Init(TIM_HandleTypeDef *htim);
HAL_StatusTypeDef HAL_TIM_OC_Start(TIM_HandleTypeDef *htim, uint32_t Channel);
HAL_StatusTypeDef HAL_ADC_Init(ADC_HandleTypeDef *hadc);
HAL_StatusTypeDef HAL_ADC_ConfigChannel(ADC_HandleTypeDef *hadc, ADC_ChannelConfTypeDef *sConfig);
HAL_StatusTypeDef HAL_ADC_Start(ADC_HandleTypeDef *hadc);
HAL_StatusTypeDef HAL_ADC_Stop(ADC_HandleTypeDef *hadc);
HAL_StatusTypeDef HAL_ADC_PollForConversion(ADC_HandleTypeDef *hadc, uint32_t Timeout);
uint32_t HAL_ADC_GetValue(ADC_HandleTypeDef *hadc);
HAL_StatusTypeDef HAL_DMA_Init(DMA_HandleTypeDef *hdma);
void HAL_NVIC_EnableIRQ(IRQn_Type IRQn);
void HAL_NVIC_DisableIRQ(IRQn_Type IRQn);
void HAL_NVIC_SetPriority(IRQn_Type IRQn, uint32_t PreemptPriority, uint32_t SubPriority);
void HAL_RCC_GPIOA_CLK_ENABLE(void);
void HAL_RCC_GPIOB_CLK_ENABLE(void);
void HAL_RCC_GPIOC_CLK_ENABLE(void);
void __disable_irq(void);
void __enable_irq(void);
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin);
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart);
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim);
void Error_Handler(void);
void SystemClock_Config(void);

/* ---------------- AVR (avr/io.h, avr/interrupt.h, util/delay.h) ---------------- */
extern volatile uint8_t DDRA, PORTA, PINA;
extern volatile uint8_t DDRB, PORTB, PINB;
extern volatile uint8_t DDRC, PORTC, PINC;
extern volatile uint8_t DDRD, PORTD, PIND;
extern volatile uint8_t DDRE, PORTE, PINE;
extern volatile uint8_t DDRF, PORTF, PINF;
extern volatile uint8_t TCCR0A, TCCR0B, TCNT0, OCR0A, OCR0B, TIMSK0, TIFR0;
extern volatile uint8_t TCCR1A, TCCR1B, TCNT1, OCR1A, OCR1B, ICR1, TIMSK1, TIFR1;
extern volatile uint8_t TCCR2A, TCCR2B, TCNT2, OCR2A, OCR2B, TIMSK2, TIFR2;
extern volatile uint8_t ADCSRA, ADCSRB, ADMUX, ADCL, ADCH;
extern volatile uint16_t ADCW;
extern volatile uint8_t SPCR, SPDR, SPSR;
extern volatile uint8_t UDR0, UCSR0A, UCSR0B, UCSR0C, UBRR0L, UBRR0H;
extern volatile uint8_t EIMSK, EICRA, PCICR, PCIFR, PRR, MCUCR, MCUSR, SMCR, WDTCSR, OSCCAL;
extern volatile uint8_t TWSR, TWCR, TWDR, TWAR, TWBR;
extern volatile uint8_t ACSR;

#define ISR(vector) void __attribute__((used)) isr_##vector(void)
#define sei() __enable_irq()
#define cli() __disable_irq()
static inline void _delay_ms(double __ms) { (void)__ms; }
static inline void _delay_us(double __us) { (void)__us; }
#define F_CPU 16000000UL
#define _BV(bit) (1 << (bit))
#define bit_is_set(sfr, bit) (0)
#define bit_is_clear(sfr, bit) (0)

/* ---------------- FreeRTOS ---------------- */
typedef void* TaskHandle_t;
typedef void* QueueHandle_t;
typedef void* SemaphoreHandle_t;
typedef unsigned long TickType_t;
typedef int BaseType_t;
typedef unsigned int UBaseType_t;
#define pdTRUE 1
#define pdFALSE 0
#define pdPASS 1
#define pdFAIL 0
#define portMAX_DELAY 0xffffffffUL
#define pdMS_TO_TICKS(x) ((TickType_t)(x))
BaseType_t xTaskCreate(void *pvTaskCode, const char *name, unsigned short stack, void *params, UBaseType_t prio, TaskHandle_t *handle);
void vTaskDelay(TickType_t ticks);
void vTaskStartScheduler(void);
void vTaskDelete(TaskHandle_t handle);
QueueHandle_t xQueueCreate(UBaseType_t len, UBaseType_t size);
BaseType_t xQueueSend(QueueHandle_t q, const void *data, TickType_t t);
BaseType_t xQueueReceive(QueueHandle_t q, void *data, TickType_t t);
SemaphoreHandle_t xSemaphoreCreateMutex(void);
BaseType_t xSemaphoreTake(SemaphoreHandle_t s, TickType_t t);
BaseType_t xSemaphoreGive(SemaphoreHandle_t s);
#define configASSERT(x) ((void)0)

/* ---------------- Zephyr (minimal) ---------------- */
struct device { int dummy; };
struct gpio_dt_spec { const struct device *port; uint8_t pin; uint8_t dt_flags; };
#define DEVICE_DT_GET(x) ((const struct device*)0)
#define DT_NODELABEL(x) 0
#define DT_ALIAS(x) 0
#define GPIO_DT_SPEC_GET(node, prop) ((struct gpio_dt_spec){0,0,0})
#define DT_PROP(x, y) 0
int printk(const char *fmt, ...);
void k_msleep(int ms);
void k_sleep(TickType_t t);
#define LOG_INF(...) ((void)0)
#define LOG_ERR(...) ((void)0)
#define LOG_DBG(...) ((void)0)
#define LOG_WRN(...) ((void)0)

/* ---------------- Raspberry Pi Pico (minimal) ---------------- */
void gpio_init(uint32_t gpio);
void gpio_set_dir(uint32_t gpio, uint32_t dir);
void gpio_put(uint32_t gpio, uint32_t value);
int gpio_get(uint32_t gpio);
void gpio_set_function(uint32_t gpio, uint32_t fn);
void stdio_init_all(void);
void sleep_ms(uint32_t ms);
void sleep_us(uint32_t us);
uint32_t time_us_32(void);
#define PICO_ERROR_NONE 0

/* ---------------- ESP-IDF (ESP32) ----------------
 * Added in round08. The header directories driver/, esp_adc/, freertos/ already
 * existed but declared no types, so ordinary ESP-IDF code was auto-stubbed as
 * `typedef struct {int _stub_;} esp_err_t;` and then reported *genuine* C errors
 * ("invalid initializer", "field name not in record or union initializer") for
 * code that is in fact correct. That misclassified a missing-SDK gap as a code
 * defect on the ESP32 tasks. These declarations follow the real ESP-IDF
 * signatures so only true defects remain.
 */
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_ERR_NO_MEM 0x101
#define ESP_ERR_INVALID_ARG 0x102
#define ESP_ERR_INVALID_STATE 0x103
#define ESP_ERR_INVALID_SIZE 0x104
#define ESP_ERR_NOT_FOUND 0x105
#define ESP_ERR_TIMEOUT 0x107
#define ESP_ERR_INVALID_RESPONSE 0x108
#define ESP_ERR_INVALID_CRC 0x109
const char *esp_err_to_name(esp_err_t code);
#define ESP_ERROR_CHECK(x) do { esp_err_t __e = (x); (void)__e; } while (0)
#define ESP_ERROR_CHECK_WITHOUT_ABORT(x) (x)
int esp_log_write(int level, const char *tag, const char *fmt, ...);
#define ESP_LOGE(tag, ...) ((void)0)
#define ESP_LOGW(tag, ...) ((void)0)
#define ESP_LOGI(tag, ...) ((void)0)
#define ESP_LOGD(tag, ...) ((void)0)
#define ESP_LOGV(tag, ...) ((void)0)
#define IRAM_ATTR
#define DRAM_ATTR
#define ESP_INTR_FLAG_IRAM (1<<9)
#define ESP_INTR_FLAG_LEVEL1 (1<<1)
void esp_restart(void);
uint32_t esp_random(void);
int64_t esp_timer_get_time(void);
void ets_delay_us(uint32_t us);

/* --- ESP-IDF GPIO --- */
typedef int gpio_num_t;
#define GPIO_NUM_0 0
#define GPIO_NUM_1 1
#define GPIO_NUM_2 2
#define GPIO_NUM_4 4
#define GPIO_NUM_5 5
#define GPIO_NUM_12 12
#define GPIO_NUM_13 13
#define GPIO_NUM_14 14
#define GPIO_NUM_15 15
#define GPIO_NUM_16 16
#define GPIO_NUM_17 17
#define GPIO_NUM_18 18
#define GPIO_NUM_19 19
#define GPIO_NUM_21 21
#define GPIO_NUM_22 22
#define GPIO_NUM_23 23
#define GPIO_NUM_25 25
#define GPIO_NUM_26 26
#define GPIO_NUM_27 27
#define GPIO_NUM_32 32
#define GPIO_NUM_33 33
#define GPIO_NUM_34 34
#define GPIO_NUM_35 35
#define GPIO_NUM_36 36
#define GPIO_NUM_39 39
typedef int gpio_mode_t;
/* GPIO_MODE_INPUT / _OUTPUT_OD already exist above with STM32 values. The exact
 * numeric value is irrelevant for a compile check, so keep the first definition
 * and only add the names ESP-IDF adds. */
#define GPIO_MODE_DISABLE 0
#ifndef GPIO_MODE_INPUT
#define GPIO_MODE_INPUT 1
#endif
#define GPIO_MODE_OUTPUT 2
#ifndef GPIO_MODE_OUTPUT_OD
#define GPIO_MODE_OUTPUT_OD 3
#endif
#define GPIO_MODE_INPUT_OUTPUT 4
typedef int gpio_pullup_t;
typedef int gpio_pulldown_t;
#define GPIO_PULLUP_DISABLE 0
#define GPIO_PULLUP_ENABLE 1
#define GPIO_PULLDOWN_DISABLE 0
#define GPIO_PULLDOWN_ENABLE 1
typedef int gpio_int_type_t;
#define GPIO_INTR_DISABLE 0
#define GPIO_INTR_POSEDGE 1
#define GPIO_INTR_NEGEDGE 2
#define GPIO_INTR_ANYEDGE 3
#define GPIO_INTR_LOW_LEVEL 4
#define GPIO_INTR_HIGH_LEVEL 5
typedef struct {
    uint64_t pin_bit_mask;
    gpio_mode_t mode;
    gpio_pullup_t pull_up_en;
    gpio_pulldown_t pull_down_en;
    gpio_int_type_t intr_type;
} gpio_config_t;
esp_err_t gpio_config(const gpio_config_t *cfg);
esp_err_t gpio_reset_pin(gpio_num_t pin);
esp_err_t gpio_set_level(gpio_num_t pin, uint32_t level);
int gpio_get_level(gpio_num_t pin);
esp_err_t gpio_set_direction(gpio_num_t pin, gpio_mode_t mode);
esp_err_t gpio_set_pull_mode(gpio_num_t pin, int pull);
esp_err_t gpio_set_intr_type(gpio_num_t pin, gpio_int_type_t type);
esp_err_t gpio_intr_enable(gpio_num_t pin);
esp_err_t gpio_intr_disable(gpio_num_t pin);
esp_err_t gpio_install_isr_service(int flags);
void gpio_uninstall_isr_service(void);
typedef void (*gpio_isr_t)(void *arg);
esp_err_t gpio_isr_handler_add(gpio_num_t pin, gpio_isr_t fn, void *arg);
esp_err_t gpio_isr_handler_remove(gpio_num_t pin);
esp_err_t gpio_wakeup_enable(gpio_num_t pin, gpio_int_type_t type);

/* --- ESP-IDF UART --- */
typedef int uart_port_t;
#define UART_NUM_0 0
#define UART_NUM_1 1
#define UART_NUM_2 2
#define UART_PIN_NO_CHANGE (-1)
typedef int uart_word_length_t;
#define UART_DATA_5_BITS 0
#define UART_DATA_6_BITS 1
#define UART_DATA_7_BITS 2
#define UART_DATA_8_BITS 3
typedef int uart_parity_t;
#define UART_PARITY_DISABLE 0
typedef int uart_stop_bits_t;
#define UART_STOP_BITS_1 1
#define UART_STOP_BITS_2 3
typedef int uart_hw_flowcontrol_t;
#define UART_HW_FLOWCTRL_DISABLE 0
#define UART_HW_FLOWCTRL_RTS 1
#define UART_HW_FLOWCTRL_CTS 2
#define UART_HW_FLOWCTRL_CTS_RTS 3
typedef int uart_sclk_t;
#define UART_SCLK_APB 0
#define UART_SCLK_DEFAULT 0
typedef struct {
    int baud_rate;
    uart_word_length_t data_bits;
    uart_parity_t parity;
    uart_stop_bits_t stop_bits;
    uart_hw_flowcontrol_t flow_ctrl;
    uint8_t rx_flow_ctrl_thresh;
    uart_sclk_t source_clk;
} uart_config_t;
esp_err_t uart_param_config(uart_port_t port, const uart_config_t *cfg);
esp_err_t uart_set_pin(uart_port_t port, int tx, int rx, int rts, int cts);
esp_err_t uart_driver_install(uart_port_t port, int rx_buf, int tx_buf, int queue_size, void *queue, int flags);
esp_err_t uart_driver_delete(uart_port_t port);
int uart_write_bytes(uart_port_t port, const void *src, size_t size);
int uart_read_bytes(uart_port_t port, void *buf, uint32_t length, TickType_t ticks);
esp_err_t uart_flush(uart_port_t port);
esp_err_t uart_get_buffered_data_len(uart_port_t port, size_t *size);
esp_err_t uart_wait_tx_done(uart_port_t port, TickType_t ticks);

/* --- ESP-IDF I2C --- */
typedef int i2c_port_t;
#define I2C_NUM_0 0
#define I2C_NUM_1 1
typedef int i2c_mode_t;
#define I2C_MODE_MASTER 1
#define I2C_MODE_SLAVE 0
#define I2C_MASTER_WRITE 0
#define I2C_MASTER_READ 1
typedef int i2c_ack_type_t;
#define I2C_MASTER_ACK 0
#define I2C_MASTER_NACK 1
#define I2C_MASTER_LAST_NACK 2
typedef struct {
    i2c_mode_t mode;
    int sda_io_num;
    int scl_io_num;
    int sda_pullup_en;
    int scl_pullup_en;
    union {
        struct { uint32_t clk_speed; } master;
        struct { uint8_t addr_10bit_en; uint16_t slave_addr; uint32_t maximum_speed; } slave;
    };
    uint32_t clk_flags;
} i2c_config_t;
typedef void *i2c_cmd_handle_t;
esp_err_t i2c_param_config(i2c_port_t port, const i2c_config_t *cfg);
esp_err_t i2c_driver_install(i2c_port_t port, i2c_mode_t mode, size_t rx_buf, size_t tx_buf, int flags);
esp_err_t i2c_driver_delete(i2c_port_t port);
i2c_cmd_handle_t i2c_cmd_link_create(void);
void i2c_cmd_link_delete(i2c_cmd_handle_t cmd);
esp_err_t i2c_master_start(i2c_cmd_handle_t cmd);
esp_err_t i2c_master_stop(i2c_cmd_handle_t cmd);
esp_err_t i2c_master_write_byte(i2c_cmd_handle_t cmd, uint8_t data, _Bool ack_en);
esp_err_t i2c_master_write(i2c_cmd_handle_t cmd, const uint8_t *data, size_t len, _Bool ack_en);
esp_err_t i2c_master_read_byte(i2c_cmd_handle_t cmd, uint8_t *data, i2c_ack_type_t ack);
esp_err_t i2c_master_read(i2c_cmd_handle_t cmd, uint8_t *data, size_t len, i2c_ack_type_t ack);
esp_err_t i2c_master_cmd_begin(i2c_port_t port, i2c_cmd_handle_t cmd, TickType_t ticks);
esp_err_t i2c_master_write_to_device(i2c_port_t port, uint8_t addr, const uint8_t *w, size_t wl, TickType_t t);
esp_err_t i2c_master_read_from_device(i2c_port_t port, uint8_t addr, uint8_t *r, size_t rl, TickType_t t);
esp_err_t i2c_master_write_read_device(i2c_port_t port, uint8_t addr, const uint8_t *w, size_t wl, uint8_t *r, size_t rl, TickType_t t);

/* --- ESP-IDF SPI --- */
typedef int spi_host_device_t;
#define SPI1_HOST 0
#define SPI2_HOST 1
#define SPI3_HOST 2
#define HSPI_HOST 1
#define VSPI_HOST 2
#define SPI_DMA_CH_AUTO 3
#define SPI_DMA_DISABLED 0
typedef struct {
    int mosi_io_num, miso_io_num, sclk_io_num, quadwp_io_num, quadhd_io_num;
    int max_transfer_sz, flags, intr_flags;
} spi_bus_config_t;
typedef struct {
    uint8_t command_bits, address_bits, dummy_bits;
    uint8_t mode;
    uint16_t duty_cycle_pos, cs_ena_pretrans, cs_ena_posttrans;
    int clock_speed_hz, input_delay_ns, spics_io_num;
    uint32_t flags;
    int queue_size;
    void *pre_cb, *post_cb;
} spi_device_interface_config_t;
typedef void *spi_device_handle_t;
typedef struct {
    uint32_t flags;
    uint16_t cmd;
    uint64_t addr;
    size_t length, rxlength;
    void *user;
    const void *tx_buffer;
    void *rx_buffer;
} spi_transaction_t;
esp_err_t spi_bus_initialize(spi_host_device_t host, const spi_bus_config_t *cfg, int dma);
esp_err_t spi_bus_free(spi_host_device_t host);
esp_err_t spi_bus_add_device(spi_host_device_t host, const spi_device_interface_config_t *cfg, spi_device_handle_t *handle);
esp_err_t spi_bus_remove_device(spi_device_handle_t handle);
esp_err_t spi_device_transmit(spi_device_handle_t handle, spi_transaction_t *t);
esp_err_t spi_device_polling_transmit(spi_device_handle_t handle, spi_transaction_t *t);
esp_err_t spi_device_queue_trans(spi_device_handle_t handle, spi_transaction_t *t, TickType_t ticks);

/* --- ESP-IDF LEDC (PWM) --- */
typedef int ledc_mode_t;
#define LEDC_LOW_SPEED_MODE 1
#define LEDC_HIGH_SPEED_MODE 0
typedef int ledc_timer_t;
#define LEDC_TIMER_0 0
#define LEDC_TIMER_1 1
#define LEDC_TIMER_2 2
#define LEDC_TIMER_3 3
typedef int ledc_channel_t;
#define LEDC_CHANNEL_0 0
#define LEDC_CHANNEL_1 1
#define LEDC_CHANNEL_2 2
#define LEDC_CHANNEL_3 3
#define LEDC_CHANNEL_4 4
#define LEDC_CHANNEL_5 5
typedef int ledc_timer_bit_t;
#define LEDC_TIMER_8_BIT 8
#define LEDC_TIMER_10_BIT 10
#define LEDC_TIMER_12_BIT 12
#define LEDC_TIMER_13_BIT 13
#define LEDC_AUTO_CLK 0
#define LEDC_INTR_DISABLE 0
#define LEDC_FADE_NO_WAIT 0
#define LEDC_FADE_WAIT_DONE 1
typedef struct {
    ledc_mode_t speed_mode;
    ledc_timer_bit_t duty_resolution;
    ledc_timer_t timer_num;
    uint32_t freq_hz;
    int clk_cfg;
} ledc_timer_config_t;
typedef struct {
    int gpio_num;
    ledc_mode_t speed_mode;
    ledc_channel_t channel;
    int intr_type;
    ledc_timer_t timer_sel;
    uint32_t duty;
    int hpoint;
    union { unsigned int output_invert; } flags;
} ledc_channel_config_t;
esp_err_t ledc_timer_config(const ledc_timer_config_t *cfg);
esp_err_t ledc_channel_config(const ledc_channel_config_t *cfg);
esp_err_t ledc_set_duty(ledc_mode_t mode, ledc_channel_t ch, uint32_t duty);
esp_err_t ledc_update_duty(ledc_mode_t mode, ledc_channel_t ch);
uint32_t ledc_get_duty(ledc_mode_t mode, ledc_channel_t ch);
esp_err_t ledc_set_freq(ledc_mode_t mode, ledc_timer_t timer, uint32_t hz);
esp_err_t ledc_fade_func_install(int flags);
esp_err_t ledc_set_fade_with_time(ledc_mode_t mode, ledc_channel_t ch, uint32_t duty, int ms);
esp_err_t ledc_fade_start(ledc_mode_t mode, ledc_channel_t ch, int wait);
esp_err_t ledc_stop(ledc_mode_t mode, ledc_channel_t ch, uint32_t idle);

/* --- ESP-IDF ADC --- */
typedef int adc1_channel_t;
typedef int adc2_channel_t;
typedef int adc_channel_t;
typedef int adc_unit_t;
typedef int adc_atten_t;
typedef int adc_bits_width_t;
typedef int adc_bitwidth_t;
#define ADC_UNIT_1 1
#define ADC_UNIT_2 2
#define ADC1_CHANNEL_0 0
#define ADC1_CHANNEL_3 3
#define ADC1_CHANNEL_4 4
#define ADC1_CHANNEL_6 6
#define ADC1_CHANNEL_7 7
#define ADC_CHANNEL_0 0
#define ADC_CHANNEL_4 4
#define ADC_CHANNEL_6 6
#define ADC_CHANNEL_7 7
#define ADC_ATTEN_DB_0 0
#define ADC_ATTEN_DB_2_5 1
#define ADC_ATTEN_DB_6 2
#define ADC_ATTEN_DB_11 3
#define ADC_ATTEN_DB_12 3
#define ADC_WIDTH_BIT_9 1
#define ADC_WIDTH_BIT_10 2
#define ADC_WIDTH_BIT_11 3
#define ADC_WIDTH_BIT_12 3
#define ADC_BITWIDTH_DEFAULT 0
#define ADC_BITWIDTH_12 12
esp_err_t adc1_config_width(adc_bits_width_t w);
esp_err_t adc1_config_channel_atten(adc1_channel_t ch, adc_atten_t atten);
int adc1_get_raw(adc1_channel_t ch);
esp_err_t adc2_get_raw(adc2_channel_t ch, adc_bits_width_t w, int *raw);
typedef void *adc_oneshot_unit_handle_t;
typedef struct { adc_unit_t unit_id; int clk_src; int ulp_mode; } adc_oneshot_unit_init_cfg_t;
typedef struct { adc_atten_t atten; adc_bitwidth_t bitwidth; } adc_oneshot_chan_cfg_t;
esp_err_t adc_oneshot_new_unit(const adc_oneshot_unit_init_cfg_t *cfg, adc_oneshot_unit_handle_t *h);
esp_err_t adc_oneshot_config_channel(adc_oneshot_unit_handle_t h, adc_channel_t ch, const adc_oneshot_chan_cfg_t *cfg);
esp_err_t adc_oneshot_read(adc_oneshot_unit_handle_t h, adc_channel_t ch, int *out);
esp_err_t adc_oneshot_del_unit(adc_oneshot_unit_handle_t h);

/* --- ESP-IDF timers / sleep --- */
typedef void *esp_timer_handle_t;
typedef void (*esp_timer_cb_t)(void *arg);
typedef struct { esp_timer_cb_t callback; void *arg; int dispatch_method; const char *name; _Bool skip_unhandled_events; } esp_timer_create_args_t;
esp_err_t esp_timer_create(const esp_timer_create_args_t *args, esp_timer_handle_t *out);
esp_err_t esp_timer_start_periodic(esp_timer_handle_t t, uint64_t us);
esp_err_t esp_timer_start_once(esp_timer_handle_t t, uint64_t us);
esp_err_t esp_timer_stop(esp_timer_handle_t t);
esp_err_t esp_timer_delete(esp_timer_handle_t t);
esp_err_t esp_sleep_enable_timer_wakeup(uint64_t us);
esp_err_t esp_sleep_enable_ext0_wakeup(gpio_num_t pin, int level);
void esp_deep_sleep_start(void);
esp_err_t esp_light_sleep_start(void);
esp_err_t esp_task_wdt_reset(void);
esp_err_t nvs_flash_init(void);

/* --- ESP-IDF FreeRTOS extras --- */
#define portTICK_PERIOD_MS 1
#define portTICK_RATE_MS 1
#define configMAX_PRIORITIES 25
#define tskIDLE_PRIORITY 0
BaseType_t xTaskCreatePinnedToCore(void *fn, const char *name, uint32_t stack, void *arg, UBaseType_t prio, TaskHandle_t *handle, int core);
TickType_t xTaskGetTickCount(void);
void vTaskDelayUntil(TickType_t *last, TickType_t period);
BaseType_t xTaskDelayUntil(TickType_t *last, TickType_t period);
BaseType_t xQueueSendFromISR(QueueHandle_t q, const void *item, BaseType_t *woken);
BaseType_t xQueueReceiveFromISR(QueueHandle_t q, void *item, BaseType_t *woken);
BaseType_t xSemaphoreGiveFromISR(SemaphoreHandle_t s, BaseType_t *woken);
SemaphoreHandle_t xSemaphoreCreateBinary(void);
SemaphoreHandle_t xSemaphoreCreateCounting(UBaseType_t max, UBaseType_t initial);
void vQueueDelete(QueueHandle_t q);
void vSemaphoreDelete(SemaphoreHandle_t s);
void taskYIELD(void);
#define portYIELD_FROM_ISR(...) ((void)0)
#define taskENTER_CRITICAL(mux) ((void)0)
#define taskEXIT_CRITICAL(mux) ((void)0)
#define portENTER_CRITICAL(mux) ((void)0)
#define portEXIT_CRITICAL(mux) ((void)0)
#define portENTER_CRITICAL_ISR(mux) ((void)0)
#define portEXIT_CRITICAL_ISR(mux) ((void)0)
typedef struct { int owner; } portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED {0}

/* ---------------- Raspberry Pi Pico (pico-sdk, extended in round08) ---------------- */
/* pico-sdk code idiomatically uses the short `uint` alias from pico/types.h */
typedef unsigned int uint;
typedef struct i2c_inst i2c_inst_t;
typedef struct uart_inst uart_inst_t;
typedef struct spi_inst spi_inst_t;
extern i2c_inst_t *i2c0;
extern i2c_inst_t *i2c1;
extern uart_inst_t *uart0;
extern uart_inst_t *uart1;
extern spi_inst_t *spi0;
extern spi_inst_t *spi1;
#define PICO_DEFAULT_LED_PIN 25
#define PICO_ERROR_GENERIC (-1)
#define PICO_ERROR_TIMEOUT (-2)
#define GPIO_OUT 1
#define GPIO_IN 0
#define GPIO_FUNC_I2C 3
#define GPIO_FUNC_SPI 1
#define GPIO_FUNC_UART 2
#define GPIO_FUNC_PWM 4
#define GPIO_IRQ_EDGE_RISE 0x8u
#define GPIO_IRQ_EDGE_FALL 0x4u
#define GPIO_IRQ_LEVEL_HIGH 0x2u
#define GPIO_IRQ_LEVEL_LOW 0x1u
#define UART_PARITY_NONE 0
#define UART_PARITY_EVEN 1
#define UART_PARITY_ODD 2
#define SPI_CPOL_0 0
#define SPI_CPOL_1 1
#define SPI_CPHA_0 0
#define SPI_CPHA_1 1
#define SPI_MSB_FIRST 1
#define SPI_LSB_FIRST 0
#define IO_IRQ_BANK0 13
#define UART0_IRQ 20
#define UART1_IRQ 21
void gpio_pull_up(uint32_t gpio);
void gpio_pull_down(uint32_t gpio);
void gpio_disable_pulls(uint32_t gpio);
void gpio_set_irq_enabled(uint32_t gpio, uint32_t events, _Bool enabled);
void gpio_set_irq_enabled_with_callback(uint32_t gpio, uint32_t events, _Bool enabled, void *cb);
void gpio_acknowledge_irq(uint32_t gpio, uint32_t events);
void irq_set_exclusive_handler(uint32_t num, void *handler);
void irq_set_enabled(uint32_t num, _Bool enabled);
void irq_set_priority(uint32_t num, uint8_t prio);
uint32_t i2c_init(i2c_inst_t *i2c, uint32_t baud);
void i2c_deinit(i2c_inst_t *i2c);
int i2c_write_blocking(i2c_inst_t *i2c, uint8_t addr, const uint8_t *src, size_t len, _Bool nostop);
int i2c_read_blocking(i2c_inst_t *i2c, uint8_t addr, uint8_t *dst, size_t len, _Bool nostop);
int i2c_write_timeout_us(i2c_inst_t *i2c, uint8_t addr, const uint8_t *src, size_t len, _Bool nostop, uint32_t us);
int i2c_read_timeout_us(i2c_inst_t *i2c, uint8_t addr, uint8_t *dst, size_t len, _Bool nostop, uint32_t us);
uint32_t uart_init(uart_inst_t *uart, uint32_t baud);
void uart_deinit(uart_inst_t *uart);
void uart_set_format(uart_inst_t *uart, uint32_t data_bits, uint32_t stop_bits, uint32_t parity);
void uart_set_fifo_enabled(uart_inst_t *uart, _Bool enabled);
void uart_set_hw_flow(uart_inst_t *uart, _Bool cts, _Bool rts);
void uart_set_irq_enables(uart_inst_t *uart, _Bool rx, _Bool tx);
void uart_puts(uart_inst_t *uart, const char *s);
void uart_putc(uart_inst_t *uart, char c);
void uart_putc_raw(uart_inst_t *uart, char c);
char uart_getc(uart_inst_t *uart);
_Bool uart_is_readable(uart_inst_t *uart);
_Bool uart_is_writable(uart_inst_t *uart);
void uart_write_blocking(uart_inst_t *uart, const uint8_t *src, size_t len);
void uart_read_blocking(uart_inst_t *uart, uint8_t *dst, size_t len);
uint32_t spi_init(spi_inst_t *spi, uint32_t baud);
void spi_set_format(spi_inst_t *spi, uint32_t bits, uint32_t cpol, uint32_t cpha, uint32_t order);
int spi_write_blocking(spi_inst_t *spi, const uint8_t *src, size_t len);
int spi_read_blocking(spi_inst_t *spi, uint8_t repeated_tx, uint8_t *dst, size_t len);
int spi_write_read_blocking(spi_inst_t *spi, const uint8_t *src, uint8_t *dst, size_t len);
void adc_init(void);
void adc_gpio_init(uint32_t gpio);
void adc_select_input(uint32_t input);
uint16_t adc_read(void);
void adc_set_temp_sensor_enabled(_Bool enable);
uint32_t pwm_gpio_to_slice_num(uint32_t gpio);
uint32_t pwm_gpio_to_channel(uint32_t gpio);
typedef struct { uint32_t csr, div, top; } pwm_config;
pwm_config pwm_get_default_config(void);
void pwm_config_set_clkdiv(pwm_config *c, float div);
void pwm_config_set_clkdiv_int(pwm_config *c, uint32_t div);
void pwm_config_set_wrap(pwm_config *c, uint16_t wrap);
void pwm_init(uint32_t slice, pwm_config *c, _Bool start);
void pwm_set_wrap(uint32_t slice, uint16_t wrap);
void pwm_set_chan_level(uint32_t slice, uint32_t chan, uint16_t level);
void pwm_set_gpio_level(uint32_t gpio, uint16_t level);
void pwm_set_enabled(uint32_t slice, _Bool enabled);
typedef struct { uint64_t _private_us_since_boot; } absolute_time_t;
struct repeating_timer { int64_t delay_us; void *callback; void *user_data; };
_Bool add_repeating_timer_ms(int32_t ms, void *cb, void *user, struct repeating_timer *out);
_Bool add_repeating_timer_us(int64_t us, void *cb, void *user, struct repeating_timer *out);
_Bool cancel_repeating_timer(struct repeating_timer *t);
absolute_time_t get_absolute_time(void);
int64_t absolute_time_diff_us(absolute_time_t from, absolute_time_t to);
uint64_t time_us_64(void);
void busy_wait_us(uint64_t us);
void multicore_launch_core1(void *entry);
void multicore_fifo_push_blocking(uint32_t data);
uint32_t multicore_fifo_pop_blocking(void);
typedef struct { int lock; } critical_section_t;
void critical_section_init(critical_section_t *cs);
void critical_section_enter_blocking(critical_section_t *cs);
void critical_section_exit(critical_section_t *cs);
void tight_loop_contents(void);

/* ---------------- CMSIS-ish ---------------- */
#define __IO volatile
typedef void (*IRQHandler)(void);

/* ---------------- ESP-IDF connectivity (WiFi/lwIP/MQTT/HTTP/SNTP) ---------- */
typedef struct esp_mqtt_client_s *esp_mqtt_client_handle_t;
typedef struct esp_http_client_s *esp_http_client_handle_t;
typedef struct esp_netif_obj esp_netif_t;
typedef struct { int uri; } esp_mqtt_broker_address_t;
typedef struct { int uri; } esp_http_client_config_uri;
esp_mqtt_client_handle_t esp_mqtt_client_init(const void *config);
int esp_mqtt_client_start(esp_mqtt_client_handle_t c);
int esp_mqtt_client_stop(esp_mqtt_client_handle_t c);
int esp_mqtt_client_subscribe(esp_mqtt_client_handle_t c, const char *topic, int qos);
int esp_mqtt_client_unsubscribe(esp_mqtt_client_handle_t c, const char *topic);
int esp_mqtt_client_publish(esp_mqtt_client_handle_t c, const char *topic,
                            const char *data, int len, int qos, int retain);
int esp_mqtt_client_register_event(esp_mqtt_client_handle_t c, void *handler, void *ctx);
int esp_mqtt_client_reconnect(esp_mqtt_client_handle_t c);
int esp_mqtt_client_disconnect(esp_mqtt_client_handle_t c);
int esp_mqtt_client_destroy(esp_mqtt_client_handle_t c);
esp_http_client_handle_t esp_http_client_init(const void *config);
int esp_http_client_perform(esp_http_client_handle_t c);
int esp_http_client_cleanup(esp_http_client_handle_t c);
int esp_http_client_set_header(esp_http_client_handle_t c, const char *k, const char *v);
int esp_http_client_fetch_headers(esp_http_client_handle_t c);
int esp_http_client_read(esp_http_client_handle_t c, char *buf, int len);
int esp_http_client_open(esp_http_client_handle_t c, int write_len);
int esp_wifi_init(const void *cfg);
int esp_wifi_start(void);
int esp_wifi_stop(void);
int esp_wifi_connect(void);
int esp_wifi_disconnect(void);
int esp_wifi_deinit(void);
int esp_wifi_set_mode(int mode);
int esp_wifi_set_config(int iface, void *conf);
int esp_wifi_set_storage(int storage);
esp_netif_t *esp_netif_create_default_wifi_station(void);
esp_netif_t *esp_netif_create_default_wifi_ap(void);
int esp_netif_init(void);
int esp_event_loop_create_default(void);
int sntp_setoperatingmode(int mode);
void sntp_setserver(int idx, void *addr);
void sntp_init(void);
void sntp_stop(void);
int esp_sntp_init(void);
int esp_sntp_stop(void);
int cyw43_arch_init(void);
void cyw43_arch_deinit(void);
void cyw43_arch_enable_station_mode(void);
void cyw43_arch_enable_ap_mode(void);
int cyw43_arch_wifi_connect_timeout_ms(const char *ssid, const char *pass, int auth, int ms);
int cyw43_arch_wifi_connect_async(const char *ssid, const char *pass, int auth);
void cyw43_arch_poll(void);
void cyw43_arch_gpio_put(int pin, _Bool v);

/* ---------------- lwIP socket types (headers are stubbed empty) ------------ */
typedef uint16_t in_port_t;
typedef uint32_t in_addr_t;
typedef uint32_t socklen_t;
typedef uint32_t sa_family_t;
struct in_addr { in_addr_t s_addr; };
struct sockaddr { sa_family_t sa_family; char sa_data[14]; };
struct sockaddr_in { sa_family_t sin_family; in_port_t sin_port;
                     struct in_addr sin_addr; unsigned char sin_zero[8]; };
struct timeval { long tv_sec; long tv_usec; };
struct hostent { char *h_name; char **h_aliases; int h_addrtype; int h_length; char **h_addr_list; };
int socket(int, int, int);
int bind(int, const struct sockaddr *, socklen_t);
int listen(int, int);
int accept(int, struct sockaddr *, socklen_t *);
int connect(int, const struct sockaddr *, socklen_t);
int recv(int, void *, size_t, int);
int send(int, const void *, size_t, int);
int recvfrom(int, void *, size_t, int, struct sockaddr *, socklen_t *);
int sendto(int, const void *, size_t, int, const struct sockaddr *, socklen_t);
int close_fn_placeholder(void);
int closesocket(int);
int shutdown(int, int);
int setsockopt(int, int, int, const void *, socklen_t);
int select(int, void *, void *, void *, struct timeval *);
uint16_t htons(uint16_t);
uint32_t htonl(uint32_t);
uint16_t ntohs(uint16_t);
uint32_t ntohl(uint32_t);
int inet_aton(const char *, struct in_addr *);
const char *inet_ntoa(struct in_addr);

/* ---------------- ESP event base (handlers compare event->base == X_EVENT) - */
typedef const char *esp_event_base_t;
esp_event_base_t WIFI_EVENT;
esp_event_base_t IP_EVENT;
esp_event_base_t ESP_EVENT_ANY_BASE;
int esp_event_handler_register(esp_event_base_t, int, void *, void *);
int esp_event_handler_unregister(esp_event_base_t, int, void *);
int esp_event_post(esp_event_base_t, int, const void *, size_t, int);

/* ---------------- ESP MQTT client structures ------------------------------- */
typedef struct esp_mqtt_event_s {
  int event_id;
  esp_mqtt_client_handle_t client;
  const char *topic;
  int topic_len;
  const char *data;
  int data_len;
  int msg_id;
  const char *msg;
  int qos;
  int retain;
  void *user_context;
} esp_mqtt_event_t;
typedef struct esp_mqtt_event_s *esp_mqtt_event_handle_t;
typedef struct { char *uri; char *host; int port; char *path; char *client_id; } esp_mqtt_address_t;
typedef struct { esp_mqtt_address_t address; } esp_mqtt_broker_t;
typedef struct { int timeout_ms; char *username; char *password; } esp_mqtt_session_t;
typedef struct {
  esp_mqtt_broker_t broker;
  esp_mqtt_session_t session;
  char *client_id;
  char *username;
  char *password;
  int keepalive;
  int disable_clean_session;
  int task_prio;
  int buffer_size;
  esp_event_base_t event_base;
} esp_mqtt_client_config_t;

/* ---------------- ESP HTTP client config ----------------------------------- */
typedef struct {
  const char *url;
  const char *host;
  int port;
  const char *path;
  const char *query;
  const char *username;
  const char *password;
  const char *method;
  int timeout_ms;
  int max_redirection_count;
  const char *cert_pem;
} esp_http_client_config_t;

/* ---------------- NimBLE GATT/GAP definitions ------------------------------ */
typedef int (*ble_gatt_access_fn)(uint16_t conn, uint16_t attr, void *ctxt, void *arg);
typedef struct ble_gatt_chr_def {
  int type;
  void *uuid;
  ble_gatt_access_fn access_cb;
  void *arg;
  int flags;
  int min_key_size;
  uint8_t val;
  const struct ble_gatt_chr_def *next;
} ble_gatt_chr_def_t;
typedef struct ble_gatt_svc_def {
  int type;
  void *uuid;
  const ble_gatt_chr_def_t *characteristics;
  const void *includes;
} ble_gatt_svc_def_t;
typedef struct { uint8_t val[16]; } ble_uuid128_t;
typedef struct { uint8_t val[2]; } ble_uuid16_t;
typedef struct { uint8_t u_type; union { ble_uuid128_t u128; ble_uuid16_t u16; } u; } ble_uuid_t;
typedef struct { uint8_t type; uint8_t length; uint8_t value[31]; } ble_hs_adv_field;
typedef struct { void *event; void *arg; } ble_gap_event_desc;
int ble_gatts_count_cfg(const void *defs);
int ble_gatts_register_services(const void *defs);
int ble_gap_adv_start(uint8_t own, void *arg, int dur, const void *params,
                      void *cb, void *cb_arg);
int ble_gap_adv_stop(void);
int ble_gap_adv_set_fields(const ble_hs_adv_field *fields);
int ble_gap_adv_rsp_set_fields(const ble_hs_adv_field *fields);
int ble_gap_disc(uint32_t own, int32_t dur, const void *params,
                 void *cb, void *cb_arg);
int ble_gap_ext_disc(uint32_t own, int16_t dur, int16_t period, void *params,
                     void *cb, void *cb_arg);
int ble_hs_sync(void);
void nimble_port_init(void);
void nimble_port_deinit(void);
void nimble_port_run(void);
int nimble_port_freertos_init(void *cb);
void nimble_port_freertos_deinit(void);

#endif /* MCU_STUB_H */
