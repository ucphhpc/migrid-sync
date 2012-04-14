/** @file
 *
 * VBox frontends: VBoxSDL (simple frontend based on SDL):
 * Implementation of MigFramebuffer (SDL framebuffer) class
 */
#include <VBox/com/com.h>
#include <VBox/com/string.h>
#include <VBox/com/Guid.h>
#include <VBox/com/ErrorInfo.h>
#include <VBox/com/EventQueue.h>
#include <VBox/com/VirtualBox.h>

#include <iprt/stream.h>
#include <iprt/env.h>

#ifdef RT_OS_OS2
# undef RT_MAX
// from <iprt/cdefs.h>
# define RT_MAX(Value1, Value2)  ((Value1) >= (Value2) ? (Value1) : (Value2))
#endif
#include "MigFramebuffer.h"

using namespace com;

#define LOG_GROUP LOG_GROUP_GUI
#include <VBox/err.h>
#include <VBox/log.h>
#include <stdio.h>

#if defined(VBOX_WITH_XPCOM)
NS_IMPL_ISUPPORTS1_CI(MigFramebuffer, IFramebuffer)
NS_DECL_CLASSINFO(MigFramebuffer)
//NS_IMPL_ISUPPORTS1_CI(MigFramebufferOverlay, IFramebufferOverlay)
//NS_DECL_CLASSINFO(MigFramebufferOverlay)
#endif

//
// Constructor / destructor
//

/**
 * SDL framebuffer constructor. It is called from the main
 * (i.e. SDL) thread. Therefore it is safe to use SDL calls
 * here.
 * @param fFullscreen    flag whether we start in fullscreen mode
 * @param fResizable     flag whether the SDL window should be resizable
 * @param fShowSDLConfig flag whether we print out SDL settings
 * @param fKeepHostRes   flag whether we switch the host screen resolution
 *                       when switching to fullscreen or not
 * @param iFixedWidth    fixed SDL width (-1 means not set)
 * @param iFixedHeight   fixed SDL height (-1 means not set)
 */
MigFramebuffer::MigFramebuffer(bool fFullscreen, bool fResizable, bool fShowSDLConfig,
                     bool fKeepHostRes, uint32_t u32FixedWidth,
                     uint32_t u32FixedHeight, uint32_t u32FixedBPP)
{
    int rc;
    LogFlow(("MigFramebuffer::MigFramebuffer\n"));
    
    ////mSurfVRAM       = NULL;
    mfInitialized   = false;
    mfFullscreen    = fFullscreen;
    mfKeepHostRes   = fKeepHostRes;
    mTopOffset      = 0;
    mfResizable     = fResizable;
    mfShowSDLConfig = fShowSDLConfig;
    mFixedSDLWidth  = u32FixedWidth;
    mFixedSDLHeight = u32FixedHeight;
    mFixedSDLBPP    = u32FixedBPP;
    mDefaultSDLBPP  = 32;
    mCenterXOffset  = 0;
    mCenterYOffset  = 0;
    /* Start with standard screen dimensions. */
    mGuestXRes      = 640;
    mGuestYRes      = 480;
    mPixelFormat    = FramebufferPixelFormat_Opaque;
    mUsesGuestVRAM  = FALSE;
    mPtrVRAM        = NULL;
    mBitsPerPixel   = 0;
    mBytesPerLine   = 0;
    mfSameSizeRequested = false;
    //mWMIcon         = NULL;

    rc = RTCritSectInit(&mUpdateLock);
    AssertMsg(rc == VINF_SUCCESS, ("Error from RTCritSectInit!\n"));

    RTPrintf("MIG:: Hey i was just started!\n");
}

MigFramebuffer::~MigFramebuffer()
{
    RTPrintf("MIG:: Hey i was just killed!\n");
    LogFlow(("MigFramebuffer::~MigFramebuffer\n"));
    RTCritSectDelete(&mUpdateLock);
}

/**
 * Returns the current framebuffer width in pixels.
 *
 * @returns COM status code
 * @param   width Address of result buffer.
 */
STDMETHODIMP MigFramebuffer::COMGETTER(Width)(ULONG *width)
{
    LogFlow(("MigFramebuffer::GetWidth\n"));
    if (!width)
        return E_INVALIDARG;
    *width = mGuestXRes;
    return S_OK;
}

/**
 * Returns the current framebuffer height in pixels.
 *
 * @returns COM status code
 * @param   height Address of result buffer.
 */
STDMETHODIMP MigFramebuffer::COMGETTER(Height)(ULONG *height)
{
    LogFlow(("MigFramebuffer::GetHeight\n"));
    if (!height)
        return E_INVALIDARG;
    *height = mGuestYRes;
    return S_OK;
}

/**
 * Lock the framebuffer (make its address immutable).
 *
 * @returns COM status code
 */
STDMETHODIMP MigFramebuffer::Lock()
{
    LogFlow(("MigFramebuffer::Lock\n"));
    RTCritSectEnter(&mUpdateLock);
    return S_OK;
}

/**
 * Unlock the framebuffer.
 *
 * @returns COM status code
 */
STDMETHODIMP MigFramebuffer::Unlock()
{
    LogFlow(("MigFramebuffer::Unlock\n"));
    RTCritSectLeave(&mUpdateLock);
    return S_OK;
}

/**
 * Return the framebuffer start address.
 *
 * @returns COM status code.
 * @param   address Pointer to result variable.
 * @TODO: implement
 */
STDMETHODIMP MigFramebuffer::COMGETTER(Address)(BYTE **address)
{
    LogFlow(("MigFramebuffer::GetAddress\n"));
    if (!address)
        return E_INVALIDARG;

    LogFlow(("VBoxSDL::GetAddress returning %p\n", *address));
    return S_OK;
}

/**
 * Return the current framebuffer color depth.
 *
 * @returns COM status code
 * @param   bitsPerPixel Address of result variable
 */
STDMETHODIMP MigFramebuffer::COMGETTER(BitsPerPixel)(ULONG *bitsPerPixel)
{
    LogFlow(("MigFramebuffer::GetBitsPerPixel\n"));
    if (!bitsPerPixel)
        return E_INVALIDARG;
    
    *bitsPerPixel = (ULONG)(16);
    return S_OK;
}

/**
 * Return the current framebuffer line size in bytes.
 *
 * @returns COM status code.
 * @param   lineSize Address of result variable.
 */
STDMETHODIMP MigFramebuffer::COMGETTER(BytesPerLine)(ULONG *bytesPerLine)
{
    LogFlow(("MigFramebuffer::GetBytesPerLine\n"));
    if (!bytesPerLine)
        return E_INVALIDARG;
    
    *bytesPerLine = (ULONG)(1);
    return S_OK;
}

STDMETHODIMP MigFramebuffer::COMGETTER(PixelFormat) (ULONG *pixelFormat)
{
    if (!pixelFormat)
        return E_POINTER;
    *pixelFormat = mPixelFormat;
    return S_OK;
}

STDMETHODIMP MigFramebuffer::COMGETTER(UsesGuestVRAM) (BOOL *usesGuestVRAM)
{
    if (!usesGuestVRAM)
        return E_POINTER;
    *usesGuestVRAM = mUsesGuestVRAM;
    return S_OK;
}

/**
 * Returns by how many pixels the guest should shrink its
 * video mode height values.
 *
 * @returns COM status code.
 * @param   heightReduction Address of result variable.
 */
STDMETHODIMP MigFramebuffer::COMGETTER(HeightReduction)(ULONG *heightReduction)
{
    if (!heightReduction)
        return E_POINTER;
    *heightReduction = 0;
    return S_OK;
}

/**
 * Returns a pointer to an alpha-blended overlay used for displaying status
 * icons above the framebuffer.
 *
 * @returns COM status code.
 * @param   aOverlay The overlay framebuffer.
 */
STDMETHODIMP MigFramebuffer::COMGETTER(Overlay)(IFramebufferOverlay **aOverlay)
{
    if (!aOverlay)
        return E_POINTER;
    /* Not yet implemented */
    *aOverlay = 0;
    return S_OK;
}

/**
 * Returns handle of window where framebuffer context is being drawn
 *
 * @returns COM status code.
 * @param   winId Handle of associated window.
 */
STDMETHODIMP MigFramebuffer::COMGETTER(WinId)(uint64_t *winId)
{
    if (!winId)
        return E_POINTER;
    *winId = mWinId;
    return S_OK;
}

/**
 * Notify framebuffer of an update.
 *
 * @returns COM status code
 * @param   x        Update region upper left corner x value.
 * @param   y        Update region upper left corner y value.
 * @param   w        Update region width in pixels.
 * @param   h        Update region height in pixels.
 * @param   finished Address of output flag whether the update
 *                   could be fully processed in this call (which
 *                   has to return immediately) or VBox should wait
 *                   for a call to the update complete API before
 *                   continuing with display updates.
 */
STDMETHODIMP MigFramebuffer::NotifyUpdate(ULONG x, ULONG y,
                                     ULONG w, ULONG h, BOOL *finished)
{
    /*
     * The input values are in guest screen coordinates.
     */
//    LogFlow(("MigFramebuffer::NotifyUpdate: x = %d, y = %d, w = %d, h = %d\n",     x, y, w, h));
    RTPrintf("MigFramebuffer::NotifyUpdate: x = %d, y = %d, w = %d, h = %d\n", x, y, w, h);
    /*
     * The Display thread can continue as we will lock the framebuffer
     * from the SDL thread when we get to actually doing the update.
     */
    if (finished)
        *finished = TRUE;
    return S_OK;
}

/**
 * Request a display resize from the framebuffer.
 *
 * @returns COM status code.
 * @param   pixelFormat The requested pixel format.
 * @param   vram        Pointer to the guest VRAM buffer (can be NULL).
 * @param   bitsPerPixel Color depth in bits.
 * @param   bytesPerLine Size of a scanline in bytes.
 * @param   w           New display width in pixels.
 * @param   h           New display height in pixels.
 * @param   finished    Address of output flag whether the update
 *                      could be fully processed in this call (which
 *                      has to return immediately) or VBox should wait
 *                      for all call to the resize complete API before
 *                      continuing with display updates.
 */
STDMETHODIMP MigFramebuffer::RequestResize(ULONG aScreenId, ULONG pixelFormat, BYTE *vram,
                                      ULONG bitsPerPixel, ULONG bytesPerLine,
                                      ULONG w, ULONG h, BOOL *finished)
{
    LogFlowFunc (("w=%d, h=%d, pixelFormat=0x%08lX, vram=%p, "
                  "bpp=%d, bpl=%d\n",
                  w, h, pixelFormat, vram, bitsPerPixel, bytesPerLine));
    RTPrintf("w=%d, h=%d, pixelFormat=0x%08lX, vram=%p, "
                  "bpp=%d, bpl=%d\n",
                  w, h, pixelFormat, vram, bitsPerPixel, bytesPerLine);

    /*
     * SDL does not allow us to make this call from any other thread than
     * the main thread (the one which initialized the video mode). So we
     * have to send an event to the main SDL thread and tell VBox to wait.
     */
    if (!finished)
    {
        AssertMsgFailed(("RequestResize requires the finished flag!\n"));
        return E_FAIL;
    }

    /*
     * Optimize the case when the guest has changed only the VRAM ptr
     * and the framebuffer uses the guest VRAM as the source bitmap.
     */
    if (   mGuestXRes    == w
        && mGuestYRes    == h
        && mPixelFormat  == pixelFormat
        && mBitsPerPixel == bitsPerPixel
        && mBytesPerLine == bytesPerLine
        && mUsesGuestVRAM
       )
    {
        mfSameSizeRequested = true;
    }
    else
    {
        mfSameSizeRequested = false;
    }

    mGuestXRes   = w;
    mGuestYRes   = h;
    mPixelFormat = pixelFormat;
    mPtrVRAM     = vram;
    mBitsPerPixel = bitsPerPixel;
    mBytesPerLine = bytesPerLine;
    mUsesGuestVRAM = FALSE; /* yet */

    /* we want this request to be processed quickly, so yield the CPU */
    RTThreadYield();

    *finished = false;

    return S_OK;
}

/**
 * Returns which acceleration operations are supported
 *
 * @returns   COM status code
 * @param     operation acceleration operation code
 * @supported result
 */
STDMETHODIMP MigFramebuffer::OperationSupported(FramebufferAccelerationOperation_T operation, BOOL *supported)
{
    if (!supported)
        return E_POINTER;

    *supported = false;

    return S_OK;
}

/**
 * Returns whether we like the given video mode.
 *
 * @returns COM status code
 * @param   width     video mode width in pixels
 * @param   height    video mode height in pixels
 * @param   bpp       video mode bit depth in bits per pixel
 * @param   supported pointer to result variable
 */
STDMETHODIMP MigFramebuffer::VideoModeSupported(ULONG width, ULONG height, ULONG bpp, BOOL *supported)
{
    if (!supported)
        return E_POINTER;

    /* are constraints set? */
    if (   (   (mMaxScreenWidth != ~(uint32_t)0)
            && (width > mMaxScreenWidth))
        || (   (mMaxScreenHeight != ~(uint32_t)0)
            && (height > mMaxScreenHeight)))
    {
        /* nope, we don't want that (but still don't freak out if it is set) */
        *supported = false;
    }
    else
    {
        /* anything will do */
        *supported = true;
    }
    return S_OK;
}

STDMETHODIMP MigFramebuffer::SolidFill(ULONG x, ULONG y, ULONG width, ULONG height,
                                  ULONG color, BOOL *handled)
{
    if (!handled)
        return E_POINTER;
    RTPrintf("SolidFill: x: %d, y: %d, w: %d, h: %d, color: %d\n", x, y, width, height, color);

    return S_OK;
}

STDMETHODIMP MigFramebuffer::CopyScreenBits(ULONG xDst, ULONG yDst, ULONG xSrc, ULONG ySrc,
                                       ULONG width, ULONG height, BOOL *handled)
{
    if (!handled)
        return E_POINTER;
    return S_OK;
}

STDMETHODIMP MigFramebuffer::GetVisibleRegion(BYTE *aRectangles, ULONG aCount,
                                         ULONG *aCountCopied)
{
  PRTRECT rects = (PRTRECT)aRectangles;

    if (!rects)
        return E_POINTER;

    /// @todo

	NOREF(aCount);
	NOREF(aCountCopied);

    return S_OK;
}

STDMETHODIMP MigFramebuffer::SetVisibleRegion(BYTE *aRectangles, ULONG aCount)
{
    PRTRECT rects = (PRTRECT)aRectangles;

    if (!rects)
        return E_POINTER;

    /// @todo

	NOREF(aCount);

    return S_OK;
}

//
// Internal public methods
//

/**
 * Method that does the actual resize of the guest framebuffer and
 * then changes the SDL framebuffer setup.
 */
void MigFramebuffer::resizeGuest()
{
    LogFlowFunc (("mGuestXRes: %d, mGuestYRes: %d\n", mGuestXRes, mGuestYRes));
    AssertMsg(mSdlNativeThread == RTThreadNativeSelf(),
              ("Wrong thread! SDL is not threadsafe!\n"));

    uint32_t Rmask, Gmask, Bmask, Amask = 0;

    mUsesGuestVRAM = FALSE;

    /* pixel characteristics. if we don't support the format directly, we will
     * fallback to the indirect 32bpp buffer (mUsesGuestVRAM will remain
     * FALSE) */
    if (mPixelFormat == FramebufferPixelFormat_FOURCC_RGB)
    {
        switch (mBitsPerPixel)
        {
            case 16:
            case 24:
            case 32:
                mUsesGuestVRAM = TRUE;
                break;
            default:
                /* the fallback buffer is always 32bpp */
                mBitsPerPixel = 32;
                mBytesPerLine = mGuestXRes * 4;
                break;
        }
    }
    else
    {
        /* the fallback buffer is always RGB, 32bpp */
        mPixelFormat = FramebufferPixelFormat_FOURCC_RGB;
        mBitsPerPixel = 32;
        mBytesPerLine = mGuestXRes * 4;
    }

    switch (mBitsPerPixel)
    {
        case 16: Rmask = 0x0000F800; Gmask = 0x000007E0; Bmask = 0x0000001F; break;
        default: Rmask = 0x00FF0000; Gmask = 0x0000FF00; Bmask = 0x000000FF; break;
    }

    LogFlow(("VBoxSDL:: created VRAM surface %p\n", mSurfVRAM));

}

/**
 * Sets SDL video mode. This is independent from guest video
 * mode changes.
 *
 * @remarks Must be called from the SDL thread!
 */
void MigFramebuffer::resizeSDL(void)
{
    LogFlow(("VBoxSDL:resizeSDL\n"));

}

/**
 * Update specified framebuffer area. The coordinates can either be
 * relative to the guest framebuffer or relative to the screen.
 *
 * @remarks Must be called from the SDL thread on Linux!
 * @param   x              left column
 * @param   y              top row
 * @param   w              width in pixels
 * @param   h              height in pixels
 * @param   fGuestRelative flag whether the above values are guest relative or screen relative;
 */
void MigFramebuffer::update(int x, int y, int w, int h, bool fGuestRelative)
{
  RTPrintf("VBoxSDL::update: %dx %dy %dw, %dh \n", x, y, w, h);
}

/**
 * Repaint the whole framebuffer
 *
 * @remarks Must be called from the SDL thread!
 */
void MigFramebuffer::repaint()
{
    LogFlow(("MigFramebuffer::repaint\n"));
    RTPrintf("MigFramebuffer::repaint\n");
    //update(0, 0, mScreen->w, mScreen->h, false /* fGuestRelative */);
    update(0, 0, 0, 0, false /* fGuestRelative */);
}

bool MigFramebuffer::getFullscreen()
{
    LogFlow(("MigFramebuffer::getFullscreen\n"));
    return mfFullscreen;
}

/**
 * Toggle fullscreen mode
 *
 * @remarks Must be called from the SDL thread!
 */
void MigFramebuffer::setFullscreen(bool fFullscreen)
{
    LogFlow(("MigFramebuffer::SetFullscreen: fullscreen: %d\n", fFullscreen));
    mfFullscreen = fFullscreen;
}

/**
 * Return the geometry of the host. This isn't very well tested but it seems
 * to work at least on Linux hosts.
 */
void MigFramebuffer::getFullscreenGeometry(uint32_t *width, uint32_t *height)
{


}

/**
 * Returns the current x offset of the start of the guest screen
 *
 * @returns current x offset in pixels
 */
int MigFramebuffer::getXOffset()
{
    /* there can only be an offset for centering */
    return mCenterXOffset;
}

/**
 * Returns the current y offset of the start of the guest screen
 *
 * @returns current y offset in pixels
 */
int MigFramebuffer::getYOffset()
{
    /* we might have a top offset and a center offset */
    return mTopOffset + mCenterYOffset;
}

/**
 * Terminate SDL
 *
 * @remarks must be called from the SDL thread!
 */
void MigFramebuffer::uninit()
{
    
}

