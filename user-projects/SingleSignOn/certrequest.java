import javax.swing.JApplet;
import java.awt.*;
import java.security.*;
import java.awt.Graphics;
import java.net.URL;
import java.net.URLConnection;
import java.applet.AppletContext.*;
import java.applet.*;
import java.io.*;
import org.bouncycastle.asn1.x509.*;
import org.bouncycastle.asn1.*;
import org.bouncycastle.jce.*;
import java.io.OutputStreamWriter;
import org.bouncycastle.openssl.PEMWriter;
import org.bouncycastle.openssl.PEMReader;
import org.bouncycastle.jce.provider.*;
import org.bouncycastle.util.encoders.Base64;
//import java.security;
import java.util.ArrayList;
import java.io.ByteArrayInputStream;
import org.bouncycastle.crypto.digests.SHA1Digest;


  
public class certrequest extends Applet {
	
	String serverUrl = "https://slcstest.uninett.no/slcsweb/";
	String uploadPage = "key_upload.php";
	
    KeyPair keypair;
    PKCS10CertificationRequest request; 
    //URLConnection con;
    boolean someError = false;
    String errorMess = "";
    URL hp;
	
    public certrequest(){
	try{
	    String url = "localhost/applet/image020.jpg";
	    hp = new URL("http", url, 80, "/");
	    //con = hp.openConnection();
	    //con.connect();
	    //Image im = getImage(hp);
	    //getAppletContext().showDocument(hp);
	}
	catch(Exception e){
	    errorMess = e.toString();
	    someError = true;
	}
    }

    public void init(){
    	
    try{
		
	Security.addProvider(new BouncyCastleProvider());	
		
	keypair = generateKeys();
	request = generateCSR(keypair);
	String csrstring = "";
	//String filename = "csrfile.pem";
	StringWriter strWrt = new StringWriter();
	
    PEMReader pemRdr = new PEMReader(
			new FileReader("/home/benjamin/.globus/usercert_request.pem"));
		PKCS10CertificationRequest readcsr = (PKCS10CertificationRequest) pemRdr.readObject();
		pemRdr.close();
    
    
   	PEMWriter pemWrt = new PEMWriter(strWrt);
	pemWrt.writeObject(readcsr);
	pemWrt.close();
    
    String csrStr = strWrt.toString();
    strWrt.close();
    
	StringWriter strWrt2 = new StringWriter();
	PEMWriter pemWrt2 = new PEMWriter(strWrt2);
	pemWrt2.writeObject(readcsr.getPublicKey());
	pemWrt2.close();
	
	String pubKeyStr = strWrt2.toString();
	byte[] digest = sha1Digest(pubKeyStr.getBytes());
	String digestStr = convertToHex(digest);
	System.out.println(digestStr);
	 
	byte[] b64Csr = base64Encode(csrStr.getBytes());
	String csrB64 = new String(b64Csr);
	String postStr = "?auth_key="+digestStr+"&remote_csr="+csrB64;
		
	String url = serverUrl+uploadPage;
	System.out.println(url+postStr);
	
	
	pushRequestToServer(url+postStr);	
	
	}
	catch(Exception e){
	    errorMess = e.toString();
	    someError = true;
	}

    }    

    private KeyPair generateKeys() throws java.security.NoSuchAlgorithmException, java.security.NoSuchProviderException{
	
	KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA", "BC");
	SecureRandom random = SecureRandom.getInstance("SHA1PRNG", "SUN");
	keyGen.initialize(2048, random);
	
	KeyPair pair = keyGen.generateKeyPair();
	
	return pair;
    }
    
    
    private PKCS10CertificationRequest generateCSR (KeyPair pair) {
   	PKCS10CertificationRequest csr = null;
    	try{
    	
    	 csr = new PKCS10CertificationRequest(
    		"SHA256withRSA",
    		new X509Principal("CN=Requested test certificate"),
    		pair.getPublic(),
    		null,
    		pair.getPrivate());
    	} catch(Exception e){
    		System.out.println("Exception: "+e.toString());
    	}
    	return csr;
    	}
    

	private void pushRequestToServer(String url){
		String spec = "search?q=hejsa";
		String testurl = "http://www.google.com/search?q=hejsa";
		//String urlName = "http://www.youtube.com/watch?v=T4bDdjgVtAc&feature=rec-HM-rev-rn";
	    try{
	    		
		System.out.println(url);
		this.getAppletContext().showDocument(new URL(url), "_self");
		
		}catch(Exception e){
			System.err.println(e.toString());
			}
		}


	private byte[] base64Encode(byte[] data){
		Base64 b64encoder = new Base64();
		byte[] b64data = b64encoder.encode(data);
		return b64data;
		}


	private byte[] sha1Digest(byte[] data) throws NoSuchAlgorithmException, IOException {
	
    MessageDigest md = MessageDigest.getInstance("SHA1");
  	md.update(data);
	byte[] digest = md.digest();
	
	return digest;
	}


    public void paint(Graphics g) {
		g.drawRect(0, 0, 500, 300);
		if(someError){
	    	g.drawString(errorMess, 5, 35);
		}
		Image im = getImage(hp);
		g.drawImage(im, 100, 100, this);
	
    }



	private void writeToFile(String data){
		String filename = "testfile.txt";
		try {
        	BufferedWriter out = new BufferedWriter(new FileWriter(filename));
        	out.write(data);
        	out.close();
    	} catch (IOException e) {
    		
    		}
		}

	private static String convertToHex(byte[] data) {
        StringBuffer buf = new StringBuffer();
        for (int i = 0; i < data.length; i++) {
        	int halfbyte = (data[i] >>> 4) & 0x0F;
        	int two_halfs = 0;
        	do {
	            if ((0 <= halfbyte) && (halfbyte <= 9))
	                buf.append((char) ('0' + halfbyte));
	            else
	            	buf.append((char) ('a' + (halfbyte - 10)));
	            halfbyte = data[i] & 0x0F;
        	} while(two_halfs++ < 1);
        }
        return buf.toString();
    }

}
