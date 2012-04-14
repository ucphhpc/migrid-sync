/** @file
 *
 * Declaration of MigFramebuffer class
 */
#ifndef __H_FRAMEBUFFER
#define __H_FRAMEBUFFER

#include <iprt/thread.h>
#include <iprt/critsect.h>

//class MigFramebufferOverlay;

class MigFramebuffer :
    public IFramebuffer
{
public:
    MigFramebuffer(bool fFullscreen = false, bool fResizable = true, bool fShowSDLConfig = false,
              bool fKeepHostRes = false, uint32_t u32FixedWidth = ~(uint32_t)0,
              uint32_t u32FixedHeight = ~(uint32_t)0, uint32_t u32FixedBPP = ~(uint32_t)0);
    virtual ~MigFramebuffer();

    NS_DECL_ISUPPORTS

    STDMETHOD(COMGETTER(Width))(ULONG *width);
    STDMETHOD(COMGETTER(Height))(ULONG *height);
    STDMETHOD(Lock)();
    STDMETHOD(Unlock)();
    STDMETHOD(COMGETTER(Address))(BYTE **address);
    STDMETHOD(COMGETTER(BitsPerPixel))(ULONG *bitsPerPixel);
    STDMETHOD(COMGETTER(BytesPerLine))(ULONG *bytesPerLine);
    STDMETHOD(COMGETTER(PixelFormat)) (ULONG *pixelFormat);
    STDMETHOD(COMGETTER(UsesGuestVRAM)) (BOOL *usesGuestVRAM);
    STDMETHOD(COMGETTER(HeightReduction)) (ULONG *heightReduction);
    STDMETHOD(COMGETTER(Overlay)) (IFramebufferOverlay **aOverlay);
    STDMETHOD(COMGETTER(WinId)) (uint64_t *winId);

    STDMETHOD(NotifyUpdate)(ULONG x, ULONG y,
                            ULONG w, ULONG h, BOOL *finished);
    STDMETHOD(RequestResize)(ULONG aScreenId, ULONG pixelFormat, BYTE *vram,
                             ULONG bitsPerPixel, ULONG bytesPerLine,
                             ULONG w, ULONG h, BOOL *finished);
    STDMETHOD(OperationSupported)(FramebufferAccelerationOperation_T operation, BOOL *supported);
    STDMETHOD(VideoModeSupported)(ULONG width, ULONG height, ULONG bpp, BOOL *supported);
    STDMETHOD(SolidFill)(ULONG x, ULONG y, ULONG width, ULONG height,
                         ULONG color, BOOL *handled);
    STDMETHOD(CopyScreenBits)(ULONG xDst, ULONG yDst, ULONG xSrc, ULONG ySrc,
                              ULONG width, ULONG height, BOOL *handled);

    STDMETHOD(GetVisibleRegion)(BYTE *aRectangles, ULONG aCount, ULONG *aCountCopied);
    STDMETHOD(SetVisibleRegion)(BYTE *aRectangles, ULONG aCount);

    // internal public methods
    bool initialized() { return mfInitialized; }
    void resizeGuest();
    void resizeSDL();
    void update(int x, int y, int w, int h, bool fGuestRelative);
    void repaint();
    bool getFullscreen();
    void setFullscreen(bool fFullscreen);
    int  getXOffset();
    int  getYOffset();
    void getFullscreenGeometry(uint32_t *width, uint32_t *height);
    uint32_t getGuestXRes() { return mGuestXRes; }
    uint32_t getGuestYRes() { return mGuestYRes; }
    void uninit();
    void setWinId(uint64_t winId) { mWinId = winId; }

private:
    /** the sdl thread */
//    RTNATIVETHREAD mSdlNativeThread;
    /** current SDL framebuffer pointer (also includes screen width/height) */
  //  SDL_Surface *mScreen;
    /** false if constructor failed */
    bool mfInitialized;
    /** maximum possible screen width in pixels (~0 = no restriction) */
    uint32_t mMaxScreenWidth;
    /** maximum possible screen height in pixels (~0 = no restriction) */
    uint32_t mMaxScreenHeight;
    /** current guest screen width in pixels */
    ULONG mGuestXRes;
    /** current guest screen height in pixels */
    ULONG mGuestYRes;
    /** fixed SDL screen width (~0 = not set) */
    uint32_t mFixedSDLWidth;
    /** fixed SDL screen height (~0 = not set) */
    uint32_t mFixedSDLHeight;
    /** fixed SDL bits per pixel (~0 = not set) */
    uint32_t mFixedSDLBPP;
    /** default BPP */
    uint32_t mDefaultSDLBPP;
    /** Y offset in pixels, i.e. guest-nondrawable area at the top */
    uint32_t mTopOffset;
    /** X offset for guest screen centering */
    uint32_t mCenterXOffset;
    /** Y offset for guest screen centering */
    uint32_t mCenterYOffset;
    /** flag whether we're in fullscreen mode */
    bool  mfFullscreen;
    /** flag wheter we keep the host screen resolution when switching to
     *  fullscreen or not */
    bool  mfKeepHostRes;
    /** framebuffer update semaphore */
    RTCRITSECT mUpdateLock;
    /** flag whether the SDL window should be resizable */
    bool mfResizable;
    /** flag whether we print out SDL information */
    bool mfShowSDLConfig;
    /** handle to window where framebuffer context is being drawn*/
    uint64_t mWinId;

//    SDL_Surface *mSurfVRAM;

    BYTE *mPtrVRAM;
    ULONG mBitsPerPixel;
    ULONG mBytesPerLine;
    ULONG mPixelFormat;
    BOOL mUsesGuestVRAM;
    BOOL mfSameSizeRequested;

    /** the application Icon */
 //   SDL_Surface *mWMIcon;
};


#ifdef hejsa
class MigFramebufferOverlay :
    public IFramebufferOverlay
{
public:
    MigFramebufferOverlay(ULONG x, ULONG y, ULONG width, ULONG height, BOOL visible,
                     MigFramebuffer *aParent);
    virtual ~MigFramebufferOverlay();

    NS_DECL_ISUPPORTS

    STDMETHOD(COMGETTER(X))(ULONG *x);
    STDMETHOD(COMGETTER(Y))(ULONG *y);
    STDMETHOD(COMGETTER(Width))(ULONG *width);
    STDMETHOD(COMGETTER(Height))(ULONG *height);
    STDMETHOD(COMGETTER(Visible))(BOOL *visible);
    STDMETHOD(COMSETTER(Visible))(BOOL visible);
    STDMETHOD(COMGETTER(Alpha))(ULONG *alpha);
    STDMETHOD(COMSETTER(Alpha))(ULONG alpha);
    STDMETHOD(COMGETTER(Address))(ULONG *address);
    STDMETHOD(COMGETTER(BytesPerLine))(ULONG *bytesPerLine);

    /* These are not used, or return standard values. */
    STDMETHOD(COMGETTER(BitsPerPixel))(ULONG *bitsPerPixel);
    STDMETHOD(COMGETTER(PixelFormat)) (ULONG *pixelFormat);
    STDMETHOD(COMGETTER(UsesGuestVRAM)) (BOOL *usesGuestVRAM);
    STDMETHOD(COMGETTER(HeightReduction)) (ULONG *heightReduction);
    STDMETHOD(COMGETTER(Overlay)) (IFramebufferOverlay **aOverlay);
    STDMETHOD(COMGETTER(WinId)) (ULONG64 *winId);

    STDMETHOD(Lock)();
    STDMETHOD(Unlock)();
    STDMETHOD(Move)(ULONG x, ULONG y);
    STDMETHOD(NotifyUpdate)(ULONG x, ULONG y,
                            ULONG w, ULONG h, BOOL *finished);
    STDMETHOD(RequestResize)(ULONG aScreenId, ULONG pixelFormat, ULONG vram,
                             ULONG bitsPerPixel, ULONG bytesPerLine,
                             ULONG w, ULONG h, BOOL *finished);
    STDMETHOD(OperationSupported)(FramebufferAccelerationOperation_T operation,
                                  BOOL *supported);
    STDMETHOD(VideoModeSupported)(ULONG width, ULONG height, ULONG bpp, BOOL *supported);
    STDMETHOD(SolidFill)(ULONG x, ULONG y, ULONG width, ULONG height,
                         ULONG color, BOOL *handled);
    STDMETHOD(CopyScreenBits)(ULONG xDst, ULONG yDst, ULONG xSrc, ULONG ySrc,
                              ULONG width, ULONG height, BOOL *handled);

    // internal public methods
    HRESULT init();

private:
    /** Overlay X offset */
    ULONG mOverlayX;
    /** Overlay Y offset */
    ULONG mOverlayY;
    /** Overlay width */
    ULONG mOverlayWidth;
    /** Overlay height */
    ULONG mOverlayHeight;
    /** Whether the overlay is currently active */
    BOOL mOverlayVisible;
    /** The parent IFramebuffer */
    MigFramebuffer *mParent;
    /** SDL surface containing the actual framebuffer bits */
    SDL_Surface *mOverlayBits;
    /** Additional SDL surface used for combining the framebuffer and the overlay */
    SDL_Surface *mBlendedBits;

};
#endif

#endif // __H_FRAMEBUFFER
